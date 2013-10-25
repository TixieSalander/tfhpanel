<%inherit file="layout.mako" />

<h2>${_('Settings')}</h2>

${form.render(object) | n}

<p>Groups:
% for group in request.user.groups:
    ${group.name}
% endfor
</p>

