<%inherit file="layout.mako" />

<h2>${_('Settings')}</h2>
<div class="width100">
    ${form.render(request, object) | n}

    <p><b>Groups:</b></p>
    <ul>
    % for group in request.user.groups:
        <li>${group.description}</li>
    % endfor
    </ul>
    </p>
</div>

