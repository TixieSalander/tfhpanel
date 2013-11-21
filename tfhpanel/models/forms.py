import re
import crypt
from pyramid.renderers import render
from collections import OrderedDict
import cgi
import pgpdump
import binascii

from .db import DBSession

from pyramid.i18n import TranslationStringFactory
_ = TranslationStringFactory('pyramid')

class IgnoreValue(object):
    pass

def escape_input(value):
    return cgi.escape(value)

class ValidationError(Exception):
    def __init__(self, message):
        self.message = message

class FormField(object):
    creation_counter = 0
    
    def __init__(self, *args, **kwargs):
        self.creation_counter = FormField.creation_counter
        FormField.creation_counter += 1

        self.label = kwargs.get('label', args[0] if len(args)>0 else False)
        self.readonly = kwargs.get('readonly', False)
        self.immutable = kwargs.get('immutable', False) # Cannot be changed after insert
        self.required = kwargs.get('required', True)
        self.type = kwargs.get('type', '')
        self.classes = kwargs.get('classes', [])

        self.validators = kwargs.get('v', [])
        if not isinstance(self.validators, list):
            self.validators = [self.validators]
    
    def validate(self, in_value):
        for validator in self.validators:
            if not validator(in_value):
                return False
        return True

    def render_label(self):
        if self.label:
            text = self.label
            if self.required:
                text = '<b>%s</b>'%text
            return '<label for="%s">%s</label>\n'%(self.uid, text)
        return ''

    def render_input(self, value, request):
        output = '<input type="%s" name="%s" '%(self.type, self.uid)
        if self.classes:
            output += 'class="%s" ' % ' '.join(self.classes)
        output += 'id="%s" ' % self.uid
        if self.readonly or self.immutable and value:
            output += 'readonly="readonly" '
        if self.required:
            output += 'required="required" '
        output += 'value="%s" ' % escape_input(value) if value else ''
        output += '/>\n'
        return output
    
    def render(self, value, request):
        raise NotImplementedError()

    def eval(self, input, request):
        raise NotImplementedError()

class ChoicesField(FormField):
    ''' <select> field
        choices: [ (0, 'Zero'), (1, 'One') ]
    '''

    def __init__(self, *args, **kwargs):
        self.choices = kwargs.get('choices')
        super().__init__(*args, **kwargs)
    
    def render_input(self, value, request):
        output = '<select name="%s" id="%s" ' % (self.uid, self.uid)
        if self.classes:
            output += 'class="%s" ' % ' '.join(self.classes)
        if self.readonly or self.immutable and value:
            output += 'disabled="disabled" '
        if self.required:
            output += 'required="required" '
        output += '>\n'
        for i, (v, label) in enumerate(self.choices):
            output += '<option value="%s"%s>%s</option>\n' % (i,
                ' selected="selected"' if value and value == v else '',
                escape_input(label))
        output += '</select>\n'
        return output
    
    def render(self, value, request):
        return self.render_label() + self.render_input(value, request)
    
    def eval(self, in_value, request):
        for i, (v, l) in enumerate(self.choices):
            if str(i) == in_value:
                return v
        return None

class TextField(FormField):
    ''' Simple text input field '''
    def __init__(self, *args, **kwargs):
        kwargs['type'] = 'text'
        self.min_len = kwargs.get('min_len', 0)
        self.max_len = kwargs.get('max_len', 1 << 20)
        self.regexp = kwargs.get('regexp', None)
        super().__init__(*args, **kwargs)
    def validate(self, in_value):
        if (self.min_len and len(in_value) < self.min_len) \
         or (self.max_len and len(in_value) > self.max_len):
            raise ValidationError('%s -> %s' % (self.min_len, self.max_len) + _(' characters.'))
        if self.regexp and not re.match(self.regexp, in_value):
            raise ValidationError(None)
            
        return super().validate(in_value)
    def render(self, value, request):
        return self.render_label() + self.render_input(str(value or ''), request)
    def eval(self, value, request):
        if value == '':
            value = None
        return value

class LargeTextField(FormField):
    ''' TextArea '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def render_input(self, value, request):
        output = '<textarea name="%s" id="%s"' % (self.uid, self.uid)
        if self.classes:
            output += 'class="%s" ' % ' '.join(self.classes)
        if self.readonly or self.immutable and value:
            output += 'readonly="readonly" '
        output += '>%s</textarea>\n' % (escape_input(value) if value else '')
        return output
    
    def render(self, value, request):
        return self.render_label() + self.render_input(str(value or ''), request)
    
    def eval(self, value, request):
        if value == '':
            value = None
        return value

class PGPKeyField(LargeTextField):
    ''' PGP field '''
    SIGNATURE = pgpdump.packet.SignaturePacket
    PUBKEY = pgpdump.packet.PublicKeyPacket

    def __init__(self, *args, **kwargs):
        self.require = kwargs.get('require', None)
        super().__init__(*args, **kwargs)
    
    def render(self, value, request):
        if not value:
            return super().render(_('No public key.\nPaste your ASCII-armored pubkey here.'), request)
        data = pgpdump.BinaryData(value)
        packets = list(data.packets())
        if packets:
            value = 'Imported Key:\n0x'+(packets[0].key_id.decode('utf-8'))
        else:
            value = ''
        return super().render(value, request)

    def eval(self, value, request):
        if '--' not in value:
            # best way i found to ignore unchanged fields.
            return IgnoreValue()
        try:
            data = pgpdump.AsciiData(bytes(value, 'utf-8'))
        except binascii.Error:
            raise ValidationError(_('Invalid PGP key'))

        packets = list(data.packets())
        if not packets:
            return IgnoreValue()

        packet = packets[0]
        if not packet:
            raise ValidationError(_('Invalid PGP key (format)'))
        if self.require and not isinstance(packet, self.require):
            raise ValidationError(_('Invalid PGP key (type)'))
        
        return data.data


class IntegerField(FormField):
    def __init__(self, *args, **kwargs):
        kwargs['type'] = 'text'
        super().__init__(*args, **kwargs)
    def validate(self, value):
        try:
            int(value)
        except ValueError:
            raise ValidationError(_('Not an integer'))
        return super().validate(value)
    def render(self, value, request):
        if value is None:
            value = ''
        return self.render_label() + self.render_input(str(value), request)
    def eval(self, value, request):
        return int(value)

class PasswordField(FormField):
    ''' Password field, crypt() input, dont output anything.
        It only replaces stored password if input != ''.
    '''

    def __init__(self, *args, **kwargs):
        kwargs['type'] = 'password'
        kwargs['required'] = False
        super().__init__(*args, **kwargs)
    
    def render_input(self, value, request):
        output = '<input type="%s" name="%s" '%(self.type, self.uid)
        if self.classes:
            output += 'class="%s" ' % ' '.join(self.classes)
        output += 'id="%s" ' % self.uid
        if self.readonly or self.immutable and value:
            output += 'readonly="readonly" '
        if self.required and not value:
            output += 'required="required" '
        if value:
            output += 'placeholder="&lt;%s&gt;" ' % _('keep empty to not change')
        output += '/>\n'
        return output

    def render(self, value, request):
        return self.render_label() + self.render_input(value, request)
    
    def eval(self, value, request):
        if not value:
            return IgnoreValue()
        if len(value) > 1024:
            raise ValidationError(_('too long. (>1024)'))
        return crypt.crypt(value)

class CheckboxField(FormField):
    def __init__(self, *args, **kwargs):
        kwargs['type'] = 'checkbox'
        
        # Never required: no data = false. no field = false.
        kwargs['required'] = False
        
        super().__init__(*args, **kwargs)
    
    def render(self, value, request):
        output = '<input type="%s" '%(self.type)
        output += 'name="%s" ' % self.uid
        if self.classes:
            output += 'class="%s" ' % ' '.join(self.classes)
        output += 'id="%s" ' % self.uid
        if self.readonly or self.immutable and value:
            output += 'disabled="disabled" '
        if self.required:
            output += 'required="required" '
        output += 'value="1" '
        output += 'checked="%s" ' % 'checked' if value else ''
        output += '/>\n'
        output += self.render_label()
        return output
    
    def eval(self, value, request):
        return value == '1'

class ForeignField(TextField):
    ''' Search for foreign keys by ID or natural key.
        input: #<dec id>
               0x<hex id>
               "<natural key containing #>"
               <natural key>
    '''

    def __init__(self, *args, **kwargs):
        self.foreign_model = kwargs.get('fm')
        self.query_filters = kwargs.get('qf', [])
        if isinstance(self.foreign_model, str):
            self.foreign_model = eval(self.foreign_model)
        super().__init__(*args, **kwargs)
    
    def render(self, value, request):
        return super().render(value if value else '', request)
    
    def filter_query(self, query, request):
        for qf in self.query_filters:
            query = qf(self, query, request)
        return query

    def eval(self, value, request):
        if value.startswith('0x'):
            id = int(value[2:].split(' ', 1)[0], 16)
            obj = DBSession.query(self.foreign_model).filter_by(id=id)
            obj = self.filter_query(obj, request).first()
            if obj:
                return obj
            
        if value.startswith('#'):
            id = int(value[1:].split(' ', 1)[0])
            obj = DBSession.query(self.foreign_model).filter_by(id=id)
            obj = self.filter_query(obj, request).first()
            if obj:
                return obj

        if len(value) > 2 and value[0] == '"' and value[-1] == '"':
            value = value[1:-1]

        if value == '':
            return None

        if not hasattr(self.foreign_model, 'natural_key'):
            # No natural key, can only be selected by id.
            raise ValidationError(_('Cannot search for these objects.'))

        obj = DBSession.query(self.foreign_model) \
            .filter( \
                getattr(self.foreign_model, self.foreign_model.natural_key) \
                == value \
            )
        obj = self.filter_query(obj, request).first()
        if not obj:
            raise ValidationError(_('Cannot find foreign object.'))
        return obj

class ChoicesForeignField(ForeignField):
    def __init__(self, *args, **kwargs):
        self.foreign_model = kwargs.get('fm')
        self.query_filters = kwargs.get('qf', [])
        self.multiple_values = kwargs.get('multiple_values', False)
        if isinstance(self.foreign_model, str):
            self.foreign_model = eval(self.foreign_model)
        super().__init__(*args, **kwargs)
    
    def render_input(self, value, request):
        output = '<select name="%s" id="%s" ' % (self.uid, self.uid)
        if self.multiple_values:
            output += 'multiple="multiple" '
        if self.classes:
            output += 'class="%s" ' % ' '.join(self.classes)
        if self.readonly or self.immutable and value:
            output += 'disabled="disabled" '
        if self.required:
            output += 'required="required" '
        output += '>\n'
        if not self.required:
            output += '<option value="">-</option>\n'
        items = DBSession.query(self.foreign_model)
        items = self.filter_query(items, request)
        items = items.order_by(self.foreign_model.id).all()
        for item in items:
            selected = False
            if isinstance(value, list):
                for valueitem in value:
                    if valueitem.id == item.id:
                        selected = True
                        break
            elif value:
                selected = value.id == item.id
            output += '<option value="%s"%s>%s</option>\n' % (
                item.id,
                ' selected="selected"' if selected else '', 
                escape_input(item.get_natural_key()))
        output += '</select>\n'
        return output
    
    def render(self, value, request):
        return self.render_label() + self.render_input(value, request)
    
    def eval(self, in_value, request):
        try:
            if self.multiple_values and isinstance(in_value, list):
                values = []
                for item in in_value:
                    q = DBSession.query(self.foreign_model)
                    q = self.filter_query(q, request)
                    q = q.filter_by(id=int(str(item))).first()
                    values.append(q)
                return values
            else:
                q = DBSession.query(self.foreign_model)
                q = self.filter_query(q, request)
                q = q.filter_by(id=int(str(in_value))).first()
                if self.multiple_values:
                    return [q] or []
                else:
                    return q
        except ValueError:
            return [] if self.multiple_values else None
    

class OneToManyField(ForeignField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    def render(self, value, request):
        if value:
            output = ', '.join([v.get_natural_key() for v in value])
        else:
            output = ''
        return TextField.render(self, output, request)
    def eval(self, value, request):
        values = value.split(',')
        objects = []
        for item in values:
            item = item.strip()
            v = super().eval(item, request)
            if v:
                objects.append(v)
        return objects
        

class FormFieldGroup(object):
    def __init__(self, type, *fields):
        self.type = type
        self.fields = fields

class Form(object):
    def __init__(self, request, action, *args, **kwargs):
        self._request = request
        self._fields = []
        self._action = action

        self._method = kwargs.get('method', 'POST')

        # 'VHostForm' -> 'vhost'
        formname = self.__class__.__name__.lower().replace('form', '')

        for name, obj in self.__class__.__dict__.items():
            if not isinstance(obj, FormField):
                continue
            obj.name = name
            obj.uid = formname + '_' + name
            self._fields.append(obj)
            # Remove fields in instances
            setattr(self, name, None)

        self._name = formname
        self._fields.sort(key=lambda o: o.creation_counter)
        self._clean_data = []

    def render(self, request, dbo=None):
        output = '<form action="%s" method="%s">\n' %(self._action, self._method)
        for field in self._fields:
            if not dbo and field.readonly:
                # Do not show readonly field in add form
                continue
            output += field.render(getattr(dbo, field.name) if dbo else None, request)
        output += '<input type="submit" />\n'
        output += '</form>'
        return output

    def validate(self, data):
        errors = []
        for field in self._fields:
            if field.readonly:
                continue
            
            key = self._name + '_' + field.name
            if key not in data:
                if field.required:
                    return False
                in_value = None
            else:
                alldata = data.getall(key)
                in_value = alldata if len(alldata) > 1 else alldata[0]

            if field.required and not in_value:
                errors.append(_('Required field: ') + field.label or field.name)
                continue

            try:
                if in_value:
                    field.validate(in_value)
                value = field.eval(in_value, request=self._request)
                setattr(self, field.name, value)
                self._clean_data.append((field, value))
            except ValidationError as e:
                error = _('Invalid value in ') + field.label or field.name
                if e.message:
                    error += ': ' + e.message
                errors.append(error)
                continue
        return errors

    def save(self, to):
        for field, value in self._clean_data:
            if field.readonly:
                continue
            if to.id and field.immutable:
                continue
            if isinstance(value, IgnoreValue):
                continue
            setattr(to, field.name, value)
    
    def get_field(self, name):
        for f in self._fields:
            if f.name == name:
                return f
        return None


