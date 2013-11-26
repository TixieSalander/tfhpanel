import re
import crypt
from pyramid.renderers import render
from collections import OrderedDict
import cgi
import pgpdump
import binascii
import ast

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
        """
        Initialize a FormField
        
        Keyword arguments:
        label -- <label> of the field
        readonly -- cannot be changed by users
        immutable -- cannot be changed after insert by users
        admin -- hidden for users
        required -- disallow empty values
        type -- <input> type
        classes -- <input> HTML classes
        """
        self.creation_counter = FormField.creation_counter
        FormField.creation_counter += 1

        self.label = kwargs.get('label', args[0] if len(args)>0 else False)
        self.readonly = kwargs.get('readonly', False)
        self.immutable = kwargs.get('immutable', False)
        self.admin = kwargs.get('admin', False)
        self.required = kwargs.get('required', True)
        self.type = kwargs.get('type', '')
        self.classes = kwargs.get('classes', [])

        self.validators = kwargs.get('v', [])
        if not isinstance(self.validators, list):
            self.validators = [self.validators]

    def __repr__(self):
        return "%s(uid='%s', label='%s')" % (
            self.__class__.__name__, self.uid, self.label)

    def is_readonly(self, value):
        '''
        return true if field should be readonly or disabled
        '''
        return (self.readonly or (value and self.immutable)) and not self.form._admin
    
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
        if self.is_readonly(value):
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
        super(ChoicesField, self).__init__(*args, **kwargs)
    
    def render_input(self, value, request):
        output = '<select name="%s" id="%s" ' % (self.uid, self.uid)
        if self.classes:
            output += 'class="%s" ' % ' '.join(self.classes)
        if self.is_readonly(value):
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
        super(TextField, self).__init__(*args, **kwargs)
    def validate(self, in_value):
        if (self.min_len and len(in_value) < self.min_len) \
         or (self.max_len and len(in_value) > self.max_len):
            raise ValidationError('%s -> %s' % (self.min_len, self.max_len) + _(' characters.'))
        if self.regexp and not re.match(self.regexp, in_value):
            raise ValidationError(None)
            
        return super(TextField, self).validate(in_value)
    def render(self, value, request):
        return self.render_label() + self.render_input(str(value or ''), request)
    def eval(self, value, request):
        if value == '':
            value = None
        return value

class LargeTextField(FormField):
    ''' TextArea '''
    def __init__(self, *args, **kwargs):
        super(LargeTextField, self).__init__(*args, **kwargs)
    
    def render_input(self, value, request):
        output = '<textarea name="%s" id="%s"' % (self.uid, self.uid)
        if self.classes:
            output += 'class="%s" ' % ' '.join(self.classes)
        if self.is_readonly(value):
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
        super(PGPKeyField, self).__init__(*args, **kwargs)
    
    def render(self, value, request):
        if not value:
            return super(PGPKeyField, self).render(_('No public key.\nPaste your ASCII-armored pubkey here.'), request)
        data = pgpdump.BinaryData(value)
        packets = list(data.packets())
        if packets:
            value = 'Imported Key:\n0x'+(packets[0].key_id.decode('utf-8'))
        else:
            value = ''
        return super(PGPKeyField, self).render(value, request)

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
        super(IntegerField, self).__init__(*args, **kwargs)
    def validate(self, value):
        try:
            ast.literal_eval(value)
        except ValueError:
            raise ValidationError(_('Not an integer'))
        return super(IntegerField, self).validate(value)
    def render(self, value, request):
        if value is None:
            value = ''
        return self.render_label() + self.render_input(str(value), request)
    def eval(self, value, request):
        return ast.literal_eval(value)

class PasswordField(FormField):
    ''' Password field, crypt() input, dont output anything.
        It only replaces stored password if input != ''.
    '''

    def __init__(self, *args, **kwargs):
        kwargs['type'] = 'password'
        kwargs['required'] = False
        super(PasswordField, self).__init__(*args, **kwargs)
    
    def render_input(self, value, request):
        output = '<input type="%s" name="%s" '%(self.type, self.uid)
        if self.classes:
            output += 'class="%s" ' % ' '.join(self.classes)
        output += 'id="%s" ' % self.uid
        if self.is_readonly(value):
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
        
        super(CheckboxField, self).__init__(*args, **kwargs)
    
    def render(self, value, request):
        output = '<input type="%s" '%(self.type)
        output += 'name="%s" ' % self.uid
        if self.classes:
            output += 'class="%s" ' % ' '.join(self.classes)
        output += 'id="%s" ' % self.uid
        if self.is_readonly(value):
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
        super(ForeignField, self).__init__(*args, **kwargs)
    
    def render(self, value, request):
        return super(ForeignField, self).render(value if value else '', request)
    
    def filter_query(self, query, request):
        for qf in self.query_filters:
            query = qf(self, query, request)
        return query

    def eval(self, value, request):
        if value.startwith('#'):
            svalue = value.split(' ', 1)[0]
            svalue = svalue[1:]
            id = ast.literal_eval(svalue)
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
        super(ChoicesForeignField, self).__init__(*args, **kwargs)
    
    def render_input(self, value, request):
        output = '<select name="%s" id="%s" ' % (self.uid, self.uid)
        if self.multiple_values:
            output += 'multiple="multiple" '
        if self.classes:
            output += 'class="%s" ' % ' '.join(self.classes)
        if self.is_readonly(value):
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
            elif isinstance(value, self.foreign_model):
                selected = value.id == item.id
            elif isinstance(value, int):
                selected = value == item.id
            else:
                selected = value == '#'+str(item.id)
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
        super(OneToManyField, self).__init__(*args, **kwargs)
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
            v = super(OneToManyField, self).eval(item, request)
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
        self._admin = kwargs.get('admin', False)
        self._defaults = {}

        # 'VHostForm' -> 'vhost'
        formname = self.__class__.__name__.lower().replace('form', '')
        
        cls = self.__class__
        while cls:
            for name, obj in cls.__dict__.items():
                if not isinstance(obj, FormField):
                    continue
                obj.name = name
                obj.uid = formname + '_' + name
                obj.form = self
                self._fields.append(obj)
                # Remove fields in instances
                setattr(self, name, None)
            cls = cls.__base__

        self._name = formname
        self._fields.sort(key=lambda o: o.creation_counter)
        self._clean_data = []

    def render(self, request, dbo=None):
        output = '<form action="%s" method="%s">\n' %(self._action, self._method)
        for field in self._fields:
            if not dbo and field.readonly:
                # Do not show readonly field in add form
                continue
            if not self._admin and field.admin:
                # Same for admin only without being admin
                continue
            if dbo:
                value = getattr(dbo, field.name)
            elif field.name in self._defaults:
                value = self._defaults[field.name]
            else:
                value = None
            output += field.render(value, request)
        output += '<input type="submit" />\n'
        output += '</form>'
        return output

    def save(self, data, to):
        errors = []
        for field in self._fields:
            if field.readonly and not self._admin:
                continue
            if field.immutable and to.id and not self._admin:
                continue
            
            key = self._name + '_' + field.name
            if key not in data:
                if field.immutable:
                    continue
                if field.required:
                    if field.admin:
                        continue
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
                if not isinstance(value, IgnoreValue):
                    setattr(to, field.name, value)
            except ValidationError as e:
                error = _('Invalid value in ') + field.label or field.name
                if e.message:
                    error += ': ' + e.message
                errors.append(error)
                continue
        return errors

    def get_field(self, name):
        for f in self._fields:
            if f.name == name:
                return f
        return None


