<%inherit file="layout.mako" />

<h2>${panelview.make_title() | n}</h2>

% if left_template:
    <div class="right50">
        <%include file="${left_template}" />
    </div>
% endif

<div class="left50">
    ${panelview.form.render(request, object) | n}
</div>

