% if aliases:
<h3>Aliases:</h3>
<ul>
    % for alias in aliases:
    <li>${utils.format_panel_value(alias, panelview) | n}</li>
    % endfor
</ul>
% endif

