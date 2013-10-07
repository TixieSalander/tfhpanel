<%inherit file="layout.mako" />
<h2>${view.model.display_name}</h2>

<table>
    % for object in objects:
        <tr>
            <td><a href="/${object.short_name}/${object.id}"><b>${object.get_natural_key()}</b></a></td>
            % for f in view.list_fields:
                <td><a href="/${object.short_name}/${object.id}">${getattr(object, f)}</a></td>
            % endfor
        </tr>
    % endfor
</table>

