<%inherit file="../layout.mako" />

<%block name="sidemenu">
    ## FIXME: I love recursive stuff
    <h2><a href="/${view.model.short_name}/">${view.model.display_name}</a></h2>
    <ul>
        % for item in utils.get_items(view.model):
            % if item.id == view.filters['id']:
                <li class="current">
                    <a href="/${view.model.short_name}/${item.id}">
                        ${item.get_natural_key()}
                    </a>
                    <ul>
                        % for m in view.subs:
                            <li>- <a href="/${view.model.short_name}/${item.id}/${m.model.short_name}/">${m.model.display_name}</a></li>
                        % endfor
                    </ul>
                </li>
            % else:
                <li><a href="/${view.model.short_name}/${item.id}">
                        ${item.get_natural_key()}
                </a></li>
            % endif
        % endfor
    </ul>
</%block>

${self.body()}
