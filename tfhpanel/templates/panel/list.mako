<%inherit file="layout.mako" />
<h2>${panelview.model.display_name}</h2>

% if objects:
<table>
    <thead>
        <tr>
            <td><!-- natural key --></td>
         % for f in panelview.list_fields:
            % if panelview.form.get_field(f) is not None:
                <td>${panelview.form.get_field(f).label}</td>
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
            <td><a href="${utils.make_url(panelview.path, change_ids=object)}">
                <b>#${object.id} ${object.get_natural_key() if object.natural_key else ''}</b>
            </a></td>
            % for f in panelview.list_fields:
                <% value = getattr(object, f) %>
                % if value and panelview.is_model_object(value):
                    <td><a class="panel-value" href="${utils.make_url(panelview.path, change_ids=value)}">
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
    <p>${_("No {panel} entries found.").format(panel=panelview.model.display_name)}</p>
% endif

<hr />

${panelview.form.render() | n}

