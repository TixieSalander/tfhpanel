<%inherit file="layout.mako" />

<h2>${_('Settings')}</h2>
<div class="width100">
	${form.render(object, request) | n}

	<p>Groups:
	% for group in request.user.groups:
    	${group.name}
	% endfor
	</p>
</div>

