<!DOCTYPE html>
<html lang="fr">
<head>
    <title>TuxPanel</title>
    <meta charset="utf-8">
    <link rel="stylesheet" href="/static/reset.css" />
    <link rel="stylesheet" href="/static/design.css" />
    <link rel="icon" href="/static/images/favicon.png" />
</head>
<body>
    <header>
        <div id="logo">
            <h1><a href="/">TuxPanel</a></h1>
        </div>
        <nav>
            <ul>
                % for short_name, panel in utils.get_root_panels().items():
                    <li>
                        <a href="/${panel.model.__short_name__}/">
                            <img src="/static/images/nav/${panel.model.__short_name__}.png"
                                alt="${panel.model.__display_name__}" /><br/>
                            ${panel.model.__display_name__}
                        </a>
                    </li>
                % endfor
                <li><a href="/support/" title="${_('Support')}">
                        <img src="/static/images/nav/support.png" alt="${_('Support')}"/><br/>
                        ${_('Support')}
                    </a>
                </li>
                <li><a href="/user/" title="${_('Your Account')}">
                        <img src="/static/images/nav/user.png" alt="${_('Your Account')}"/><br/>
                        ${_('Your Account')}
                    </a>
                </li>
                <li><a href="/user/logout" title="${_('Logout')}" class="navlogout">
                        <img src="/static/images/nav/logout.png" alt="${_('Logout')}"/>
                    </a>
                </li>
            </ul>
        </nav>
        <div style="clear:both"></div>
    </header>
    <div class="wrap">
        <aside>
            <%block name="sidemenu"></%block>
        </aside>
        <section>
            <div id="messages">
                % for m in request.session.pop_flash():
                    <p class="message m-${m[0]}">${m[1]}</p>
                % endfor
            </div>
            <div class="content">
                
                ${next.body()}
                <div class="clear"></div>
            </div>
        </section>
    </div>
</body>
</html>

