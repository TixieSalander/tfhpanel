% if aliases:
<h3>${_('Aliases')}:</h3>
<ul>
    % for alias in aliases:
    <li>${utils.format_panel_value(alias, panelview) | n}</li>
    % endfor
</ul>
% endif
<p>${_('This mailbox has no aliases')}</p>

