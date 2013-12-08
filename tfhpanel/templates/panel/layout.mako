<%inherit file="../layout.mako" />

<%def name="fu(panellist, index=1)">
    <ul>
        % for short_name, c in panellist[0].children.items():
            <%
                newpath = panelview.path[0:index]
                newpath.append(c)
                url = utils.make_url(newpath)
            %>
            <li><a href="${url}">${c.model.__display_name__}</a>
                % if panellist[1:] and panellist[1].children:
                    ${fu(panellist[1:], index+1)}
                % endif
            </li>
        % endfor
    </ul>
</%def>

<%block name="sidemenu">
    <% url = utils.make_url(panelview.path[0:1], index=True) %>
    <h2><a href="${url}">${panelview.path[0].model.__display_name__}</a></h2>
    % if panelview.path[0].id:
        ${fu(panelview.path)}
    % else:
        <ul>
            % for item in panelview.objects:
                <% url = utils.make_url(panelview.path[0:1], change_ids=item) %>
                <li><a href="${url}">${str(item)}</a></li>
            % endfor
        </ul>
    % endif
</%block>

% if request.has_permission('panel_admin'):
    % if request.session.get('panel_admin', False):
        <p><a href="?admin=0">${_('Disable admin mode')}</a></p>
    % else:
        <p><a href="?admin=1">${_('Enable admin mode')}</a></p>
    % endif
% endif

${next.body()}

