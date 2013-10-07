<%inherit file="layout.mako" />

<h2>${_('Home')}</h2>
<div class="left50">
    <div id="infos-home">
        <h3>Bienvenue sur votre panel de gestion de compte</h3>
        <p>Il vous permet de gerer votre compte ainsi que les services associes.<br/></p>
        <ul>
            <li>La categorie <u>Mon compte</u> permet de gerer son compte Tux-FreeHost en reglant tout ce qui est informations personnelles, mot de passe du compte et paiements.</li>
            <li>La categorie <u>Hebergement web</u> permet de gerer son compte d'hebergement en reglant ses vhosts et ses bases de donnees.</li>
            <li>La categorie <u>Mail</u> permet de gerer ses comptes mails, ses listes de diffusions et d'acceder au webmail</li>
            <li>La categorie <u>Support</u> permet de contacter le support sous la forme de tickets pour tout probleme que vous n'arrivez pas a resoudre par vous-meme.</li>
        </ul>
    </div>
</div>

<div class="right50">
    <table class="stats">
        <caption>
            <h3>Mon offre</h3>
        </caption>
        <tr>
            <td>Offre</td>
            <td>Start Plan</td>
        </tr>
        <tr>
            <td>Espace disque</td>
            <td>215 MB / 400 MB</td>
        </tr>
        <tr>
            <td>Bande Passante</td>
            <td>1 GB / 20 GB</td>
        </tr>
        <tr>
            <td>Compte SQL</td>
            <td>1 / 1</td>
        </tr>
        <tr>
            <td>Bases de donnees</td>
            <td>1 / 1</td>
        </tr>
        <tr class="tfooter">
            <td><a href="">${_('Upgrade')}</a></td>
            <td></td>
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
            <td>27 Aout 2013</td>
        </tr>
        <tr>
            <td>Neque porro quisquam est qui dolorem ipsum quia dolor sit amet, consectetur, adipisci velit</td>
            <td>27 Aout 2013</td>
        </tr>
        <tr>
            <td>Neque porro quisquam est qui dolorem ipsum quia dolor sit amet, consectetur, adipisci velit</td>
            <td>27 Aout 2013</td>
        </tr>
        <tr class="tfooter">
            <td><a href="/support/">${_('More')}</a></td>
            <td></td>
        </tr>
    </table>
</div>

