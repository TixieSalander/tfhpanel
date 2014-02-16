<!DOCTYPE html>
<html lang="fr">
<head>
    <title>TuxPanel Login</title>
    <meta charset="utf-8">
    <link rel="stylesheet" href="/static/reset.css" />
    <link rel="stylesheet" href="/static/design.css" />
    <link rel="icon" href="/static/images/favicon.png" />
</head>
<body id="loginform">
    <div class="loginform">
        <h1>${_('Login')}</h1>
        
        % for m in request.session.pop_flash():
            <p class="loginmessage m-${m[0]}">${m[1]}</p>
        % endfor
        
        <div class="form">
            <form method="post" action="/user/login${'?pgp=1' if pgp else ''}" name="loginform">
                <input type="text" name="username" placeholder="${_('Username / e-mail')}" />
                % if pgp:
                    <label for="signedtoken">${_('Sign this token:')} <code>xclip -o | gpg -sab</code></label>
                    <textarea name="signedtoken" id="signedtoken">${pgp_token}</textarea>
                % else:
                    <input type="password" name="password" placeholder="${_('Password')}" />
                % endif
                <input type="submit" value="${_('Login')}"></input>
            </form>
        </div>
        % if pgp:
            &rarr; <a href="/user/login">${_('Password login')}</a><br />
        % else:
            &rarr; <a href="/user/login?pgp=1">${_('OpenPGP login')}</a><br />
            &rarr; <a href="/user/pwreset">${_('Forgot password?')}</a><br/>
        % endif
        &rarr; <a href="//tux-fh.net/">${_('Go back on Tux-FH.net')}</a>
    </div>
</body>
</html>

