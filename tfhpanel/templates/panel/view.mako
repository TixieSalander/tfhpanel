<%inherit file="layout.mako" />

<h2>${object.display_name} - ${object.get_natural_key()}</h2>

% if left_template:
    <div class="right50">
        <%include file="${left_template}" />
    </div>
% endif

<div class="left50">
    ${form.render(object) | n}
</div>

