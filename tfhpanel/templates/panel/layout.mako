<%inherit file="../layout.mako" />

<%block name="sidemenu">
    ## FIXME: I love recursive stuff
    <h2><a href="${view.make_url()}">${view.model.display_name}</a></h2>
    <ul>
        % for item in utils.get_items(view.model):
            % if item.id == view.filters['id']:
                <li class="current">
                    <a href="${view.make_url(item)}">
                        ${item.get_natural_key()}
                    </a>
                    <ul>
                        % for m in view.subs:
                            <li>- <a href="${view.make_url(item)}/${m.model.short_name}/">${m.model.display_name}</a></li>
                        % endfor
                    </ul>
                </li>
            % else:
                <li><a href="${view.make_url(item)}">
                        ${item.get_natural_key()}
                </a></li>
            % endif
        % endfor
    </ul>
</%block>

${self.body()}
