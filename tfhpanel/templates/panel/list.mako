<%inherit file="layout.mako" />
<h2>${panelview.make_title() | n}</h2>

<div class="width100">
    % if objects:
    <table>
        <thead>
            <tr>
                <td><!-- natural key --></td>
            % for f in list_fields:
                <td>${f[0]}</td>
            % endfor
            </tr>
        </thead>
        % for object in objects:
            <tr>
                <td><a href="${utils.make_url(panelview.path, change_ids=object)}">
                    <b>${str(object)}</b>
                </a></td>
                % for f in list_fields:
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
        <p>${_("No {panel} entries found.").format(panel=panelview.model.__display_name__)}</p>
    % endif

    <hr />

    ${panelview.form.render(request, defaultobject) | n}
</div>
