<!DOCTYPE html>
<html class="${properties.kcHtmlClass!}">

<head>
    <meta charset="utf-8">
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    <meta name="robots" content="noindex, nofollow">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <#if properties.meta?has_content>
        <#list properties.meta?split(' ') as meta>
            <meta name="${meta?split('==')[0]}" content="${meta?split('==')[1]}"/>
        </#list>
    </#if>

    <title>${msg("loginTitle")}</title>
    <link rel="icon" href="${url.resourcesPath}/img/favicon.ico" />

    <#if properties.stylesCommon?has_content>
        <#list properties.stylesCommon?split(' ') as style>
            <link href="${url.resourcesCommonPath}/${style}" rel="stylesheet" />
        </#list>
    </#if>
    <#if properties.styles?has_content>
        <#list properties.styles?split(' ') as style>
            <link href="${url.resourcesPath}/${style}" rel="stylesheet" />
        </#list>
    </#if>
    <#if properties.scripts?has_content>
        <#list properties.scripts?split(' ') as script>
            <script src="${url.resourcesPath}/${script}" type="text/javascript"></script>
        </#list>
    </#if>
    <#if scripts??>
        <#list scripts as script>
            <script src="${script}" type="text/javascript"></script>
        </#list>
    </#if>
    
    <#if pageRedirectUri?has_content>
        <meta http-equiv="refresh" content="0; url=${pageRedirectUri}">
    </#if>
</head>

<body class="uc1-pro-login">
    <div class="login-pf-page">
        <div class="uc1-background"></div>

        <div class="container">
            <div class="row">
                <div class="col-sm-8 col-sm-offset-2 col-md-6 col-md-offset-3 col-lg-6 col-lg-offset-3">
                    <div class="card-pf uc1-card">
                        <header class="login-pf-header">
                            <div class="uc1-logo-container">
                                <img src="${url.resourcesPath}/img/colonel-logo.png" alt="The Colonel" class="uc1-logo" />
                            </div>
                            <h1 id="kc-page-title" class="uc1-title">
                                ${msg("loginTitle")}
                            </h1>
                        </header>

                        <div id="kc-content">
                            <div id="kc-content-wrapper">
                                <#if messageHeader??>
                                    <p class="instruction" style="text-align: center; font-size: 16px; color: #333; margin-bottom: 20px;">
                                        ${messageHeader}
                                    </p>
                                </#if>

                                <#if requiredActions??>
                                    <#list requiredActions>
                                        <div class="alert alert-warning" style="margin-bottom: 20px;">
                                            <p>${msg("requiredAction.intro")}</p>
                                            <ul>
                                                <#items as reqActionItem>
                                                    <li>${msg("requiredAction.${reqActionItem}")}</li>
                                                </#items>
                                            </ul>
                                        </div>
                                    </#list>
                                <#elseif skipLink??>
                                    <div class="uc1-button-group" style="text-align: center; margin-top: 30px;">
                                        <#if pageRedirectUri?has_content>
                                            <p style="margin-bottom: 20px; font-size: 14px; color: #666;">
                                                ${kcSanitize(message.summary)?no_esc}
                                            </p>
                                            <p style="font-size: 14px; color: #888;">
                                                Redirecting automatically...
                                            </p>
                                        <#else>
                                            <#if message?has_content>
                                                <div class="alert alert-${message.type}" style="margin-bottom: 20px;">
                                                    <span class="kc-feedback-text">${kcSanitize(message.summary)?no_esc}</span>
                                                </div>
                                            </#if>
                                            <a href="${url.loginRestartFlowUrl}" class="btn btn-primary btn-block btn-lg uc1-submit-btn">
                                                ${kcSanitize(skipLinkText)?no_esc}
                                            </a>
                                        </#if>
                                    </div>
                                <#else>
                                    <#if message?has_content>
                                        <div class="alert alert-${message.type}" style="margin-bottom: 30px; text-align: center;">
                                            <#if message.type = 'success'>
                                                <span class="${properties.kcFeedbackSuccessIcon!}"></span>
                                            </#if>
                                            <#if message.type = 'warning'>
                                                <span class="${properties.kcFeedbackWarningIcon!}"></span>
                                            </#if>
                                            <#if message.type = 'error'>
                                                <span class="${properties.kcFeedbackErrorIcon!}"></span>
                                            </#if>
                                            <#if message.type = 'info'>
                                                <span class="${properties.kcFeedbackInfoIcon!}"></span>
                                            </#if>
                                            <span class="kc-feedback-text">${kcSanitize(message.summary)?no_esc}</span>
                                        </div>
                                    </#if>
                                    
                                    <div class="uc1-button-group" style="text-align: center;">
                                        <#if actionUri?has_content>
                                            <a href="${actionUri}" class="btn btn-primary btn-block btn-lg uc1-submit-btn">
                                                ${kcSanitize(actionUriText)?no_esc}
                                            </a>
                                        <#else>
                                            <a href="${url.loginRestartFlowUrl}" class="btn btn-primary btn-block btn-lg uc1-submit-btn">
                                                ${msg("backToApplication")}
                                            </a>
                                        </#if>
                                    </div>
                                </#if>
                            </div>
                        </div>

                        <footer class="uc1-footer">
                            <p>&copy; 2025 Magic Unicorn Unconventional Technology & Stuff Inc</p>
                        </footer>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>

</html>
