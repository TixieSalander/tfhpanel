<%inherit file="../layout.mako" />

<%def name="fu(panellist, index=1)">
    <ul>
        % for short_name, c in panellist[0].children.items():
            <%
                newpath = panelview.path[0:index]
                newpath.append(c)
                url = utils.make_url(newpath)
            %>
            <li><a href="${url}">${c.model.display_name}</a>
                % if panellist[1:] and panellist[1].children:
                    ${fu(panellist[1:], index+1)}
                % endif
            </li>
        % endfor
    </ul>
</%def>

<%block name="sidemenu">
    <% url = utils.make_url(panelview.path[0:1], index=True) %>
    <h2><a href="${url}">${panelview.path[0].model.display_name}</a></h2>
    % if panelview.path[0].id:
        ${fu(panelview.path)}
    % else:
        <ul>
            % for item in utils.get_items(panelview.path[0].model, filter=panelview.filter_query):
                <% url = utils.make_url(panelview.path[0:1], change_ids=item) %>
                <li><a href="${url}">${item.get_natural_key()}</a></li>
            % endfor
        </ul>
    % endif
</%block>

${self.body()}

