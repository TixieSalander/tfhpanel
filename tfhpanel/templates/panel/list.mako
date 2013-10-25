<%inherit file="layout.mako" />
<h2>${view.model.display_name}</h2>

<% print(repr(utils.get_root_panels_dict())) %>
<table>
    <thead>
        <tr>
            <td><!-- natural key --></td>
         % for f in view.list_fields:
            % if form.get_field(f) is not None:
                <td>${form.get_field(f).label}</td>
            % elif f in utils.get_root_panels_dict():
                <td>${utils.get_root_panels_dict()[f].model.display_name}</td>
            % elif f == 'user':
                <td>${_('User')}</td>
            % else:
                <td>${f}</td>
            % endif
        % endfor
        </tr>
    </thead>
    % for object in objects:
        <tr>
            <td><a href="${view.make_url(object)}"><b>${object.get_natural_key()}</b></a></td>
            % for f in view.list_fields:
                <td><a href="${view.make_url(object)}">${getattr(object, f)}</a></td>
            % endfor
        </tr>
    % endfor
</table>

${form.render() | n}

