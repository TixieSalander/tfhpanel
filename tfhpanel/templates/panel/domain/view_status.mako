% if object.verified:
    <p>${_('This domain is verified.')}</p>
% else:
    <p>${_('This domain is not verified.')}</p>
    ## TODO: Add some instructions and a refresh button
% endif

