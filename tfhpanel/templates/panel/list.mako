<%inherit file="layout.mako" />
<h2>${panelview.model.display_name}</h2>

% if objects:
<table>
    <thead>
        <tr>
            <td><!-- natural key --></td>
        % for f in panelview.list_fields:
            <td>${f[0]}</td>
        % endfor
        </tr>
    </thead>
    % for object in objects:
        <tr>
            <td><a href="${utils.make_url(panelview.path, change_ids=object)}">
                <b>#${object.id} ${object.get_natural_key() if object.natural_key else ''}</b>
            </a></td>
            % for f in panelview.list_fields:
                <%
                    if isinstance(f[1], str):
                        value = getattr(object, f[1])
                    else:
                        value = f[1](object)
                %>
                % if value is not None:
                    <td>${utils.format_panel_value(value, panelview) | n}</td>
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

