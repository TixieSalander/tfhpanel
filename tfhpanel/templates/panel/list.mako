<%inherit file="layout.mako" />
<h2>${view.model.display_name}</h2>

% if objects:
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
            <td><a href="${view.make_url(object)}">
                <b>#${object.id} ${object.get_natural_key() if object.natural_key else ''}</b>
            </a></td>
            % for f in view.list_fields:
                <% value = getattr(object, f) %>
                % if value and view.is_model_object(value):
                    <td><a class="panel-value" href="${view.make_url(value)}">
                        #${value.id} <span class="panel-value">
                            ${value.get_natural_key()}
                        </span>
                    </a></td>
                % elif value is not None:
                    <td><span class="panel-value">${value}</span></td>
                % else:
                    <td>None</td>
                % endif
            % endfor
        </tr>
    % endfor
</table>
% else:
    <p>${_("No {panel} entries found.").format(panel=view.model.display_name)}</p>
% endif

<hr />

${form.render() | n}

