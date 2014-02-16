<%inherit file="layout.mako" />

<h2>${_('Home')}</h2>
<div class="right50">
    <table class="stats">
        <caption>
            <h3>My Acccount</h3>
        </caption>
        <tr>
            <td>Disk Space Usage</td>
            <td>215 MB / 400 MB</td>
        </tr>
        <tr>
            <td>Monthly Bandwidth Transfer</td>
            <td>1 GB / 20 GB</td>
        </tr>
        <tr>
            <td>SQL Accounts</td>
            <td>1 / 1</td>
        </tr>
        <tr>
            <td>MySQL Databases</td>
            <td>1 / 1</td>
        </tr>
    </table>

    <table class="tickets-home">
        <caption>
            <h3>${_('Support Tickets')}</h3>
        </caption>
        <tr>
            <th>${_('Subject')}</th>
            <th>${_('Last message')}</th>
        </tr>
        <tr>
            <td>Neque porro quisquam est qui dolorem ipsum quia dolor sit amet, consectetur, adipisci velit</td>
            <td>27 August 2013</td>
        </tr>
        <tr>
            <td>Neque porro quisquam est qui dolorem ipsum quia dolor sit amet, consectetur, adipisci velit</td>
            <td>27 August 2013</td>
        </tr>
        <tr>
            <td>Neque porro quisquam est qui dolorem ipsum quia dolor sit amet, consectetur, adipisci velit</td>
            <td>27 August 2013</td>
        </tr>
        <tr class="tfooter">
            <td><a href="/support/">${_('More')}</a></td>
            <td></td>
        </tr>
    </table>
</div>

<div class="left50">
    <div id="infos-home">
        <h3>Welcome back on your panel</h3>
        <p>It allow you to manage your account and attached services.<br/></p>
        <ul>
            <li>The <u>Maiboxes</u> section allows you to create an email account at your domain so that you can receive email from customers or other visitors to your domain.</li>
            <li>The <u>Domains</u> section allows you to manage yours linked domains and subdomains.</li>
            <li>The <u>Vhosts</u> section allows you to link a existing domain to a folder in your home directory.</li>
            <li>The <u>My account</u> section allows you to manage your Tux-FreeHost account and configure your personal informations, password and bills.</li>
            <li>The <u>Support</u> section allows you to contact the support with tickets for problemes you couldn't manage by yourself.</li>
        </ul>
    </div>
</div>
