import re
import crypt
from pyramid.renderers import render
from tfhnode.models import *
from collections import OrderedDict
import cgi
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
        self.validator = kwargs.get('validator', None)
        self.readonly = kwargs.get('readonly', False)
        self.immutable = kwargs.get('immutable', False) # Cannot be changed after insert
        self.required = kwargs.get('required', True)
        self.type = kwargs.get('type', '')
        self.classes = kwargs.get('classes', [])
    
    def render_label(self):
        if self.label:
            return '<label for="%s">%s</label>\n'%(self.uid, self.label)
        return ''

    def render_input(self, value):
        output = '<input type="%s" name="%s" '%(self.type, self.uid)
        if self.classes:
            output += 'class="%s" ' % ' '.join(self.classes)
        output += 'id="%s" ' % self.uid
        if self.readonly or self.immutable and value:
            output += 'readonly="readonly" '
        output += 'value="%s" ' % escape_input(value) if value else ''
        output += '/>\n'
        return output
    
    def render(self, value):
        raise NotImplementedError()

    def eval(self, input, request):
        raise NotImplementedError()

class TextField(FormField):
    ''' Simple text input field '''
    def __init__(self, *args, **kwargs):
        kwargs['type'] = 'text'
        super().__init__(*args, **kwargs)
    def render(self, value):
        return self.render_label() + self.render_input(str(value or ''))
    def eval(self, value, request):
        return value

class IntegerField(FormField):
    def __init__(self, *args, **kwargs):
        kwargs['type'] = 'text'
        super().__init__(*args, **kwargs)
    def render(self, value):
        if value is None:
            value = ''
        return self.render_label() + self.render_input(str(value))
    def eval(self, value, request):
        return int(value)

class PasswordField(FormField):
    ''' Password field, crypt() input, dont output anything.
        It only replaces stored password if input != ''.
    '''

    def __init__(self, *args, **kwargs):
        kwargs['type'] = 'password'
        super().__init__(*args, **kwargs)

    def render(self, value):
        return self.render_label() + self.render_input('')
    
    def eval(self, value, request):
        if not value:
            return IgnoreValue()
        return crypt.crypt(value)

class CheckboxField(FormField):
    def __init__(self, *args, **kwargs):
        kwargs['type'] = 'checkbox'
        
        # Never required: no data = false. no field = false.
        kwargs['required'] = False
        
        super().__init__(*args, **kwargs)
    
    def render(self, value):
        output = '<input type="%s" '%(self.type)
        output += 'name="%s" ' % self.uid
        if self.classes:
            output += 'class="%s" ' % ' '.join(self.classes)
        output += 'id="%s" ' % self.uid
        if self.readonly or self.immutable and value:
            output += 'readonly="readonly" '
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
    
    def render(self, value):
        return super().render(value.get_natural_key() if value else '')
    
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

class OneToManyField(ForeignField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    def render(self, value):
        if value:
            output = ', '.join([v.get_natural_key() for v in value])
        else:
            output = ''
        return TextField.render(self, output)
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


class Validator(object):
    def __call__(self, data):
        raise NotImplementedError()

class StringValidator(Validator):
    def __init__(self, min_len=1, max_len=254):
        self.min_len = min_len
        self.max_len = max_len

    def __call__(self, data):
        return self.min_len <= len(data) <= self.max_len

class RegexpValidator(Validator):
    def __init__(self, regexp):
        if isinstance(regexp, re._pattern_type):
            self.re = regexp
        else:
            self.re = re.compile(regexp)

    def __call__(self, data):
        return self.re.match(data)


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

    def render(self, dbo=None):
        output = '<form action="%s" method="%s">\n' %(self._action, self._method)
        for field in self._fields:
            if not dbo and field.readonly:
                # Do not show readonly field in add form
                continue
            output += field.render(getattr(dbo, field.name) if dbo else None)
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
                in_value = data[key]
            
            if field.validator and not field.validator(in_value):
                errors.append(_('Invalid field: %s') % field.label or field.name)
                continue
            
            try:
                value = field.eval(in_value, request=self._request)
                setattr(self, field.name, value)
                self._clean_data.append((field, value))
            except ValidationError as e:
                errors.append(e.message)
                continue
        return errors

    def save(self, to):
        for field, value in self._clean_data:
            if field.readonly:
                continue
            if to.id and field.immutable:
                continue
            if value is IgnoreValue:
                continue
            setattr(to, field.name, value)
    
    def get_field(self, name):
        for f in self._fields:
            if f.name == name:
                return f
        return None


