<%inherit file="../layout.mako" />

<%block name="sidemenu">
    <%
        menu = (
            # route,            title
            ('user_settings',   _('Settings')),
            ('user_logout',     _('Logout')),
        )
    %>
    <h2><a href="${request.route_url('user_home')}">${_('Account')}</a></h2>
    <ul>
        % for item in menu:
            % if request.matched_route.name == item[0]:
                <li class="current">
            % else:
                <li>
            % endif
                    <a href="${request.route_url(item[0])}">${item[1]}</a>
                </li>
        % endfor
    </ul>
</%block>

${self.body()}

