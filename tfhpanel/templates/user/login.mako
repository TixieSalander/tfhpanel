<!DOCTYPE html>
<html lang="fr">
<head>
    <title>TuxPanel Login</title>
    <meta charset="utf-8">
    <link rel="stylesheet" href="/static/reset.css" />
    <link rel="stylesheet" href="/static/design.css" />
</head>
<body id="loginform">
    <div class="loginform">
        <h1>${_('Login')}</h1>
        <div class="form">
            <form method="post" action="/user/login" name="loginform">
                <input type="text" name="username" placeholder="${_('Username')}" />
                <input type="password" name="password" placeholder="${_('Password')}" />
                <input type="submit" value="${_('Login')}"></input>
            </form>
        </div>
        &rarr; <a href="/user/pwreset">${_('Forgot password?')}</a><br/>
        &rarr; <a href="//tux-fh.net/">${_('Go back on Tux-FH.net')}</a>
    </div>
</body>
</html>

