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

    <title>${msg("emailForgotTitle")}</title>
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
                                ${msg("emailForgotTitle")}
                            </h1>
                        </header>

                        <div id="kc-content">
                            <div id="kc-content-wrapper">
                                <div id="kc-form">
                                    <div id="kc-form-wrapper">
                                        <#if message?has_content && (message.type != 'warning' || !isAppInitiatedAction??)>
                                            <div class="alert alert-${message.type} uc1-message">
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

                                        <form id="kc-reset-password-form" class="form uc1-form" action="${url.loginAction}" method="post">
                                            <div class="form-group">
                                                <label for="username" class="uc1-label">${msg("usernameOrEmail")}</label>
                                                <input tabindex="1" id="username" class="form-control uc1-input" name="username" type="text"
                                                       autofocus autocomplete="username"
                                                       aria-invalid="<#if messagesPerField.existsError('username')>true</#if>" />
                                                <#if messagesPerField.existsError('username')>
                                                    <span id="input-error-username" class="uc1-error" aria-live="polite">
                                                        ${kcSanitize(messagesPerField.get('username'))?no_esc}
                                                    </span>
                                                </#if>
                                            </div>

                                            <div id="kc-form-buttons" class="form-group uc1-button-group" style="margin-top: 20px;">
                                                <input class="btn btn-primary btn-block btn-lg uc1-submit-btn" type="submit" value="${msg("doSubmit")}"/>
                                            </div>
                                        </form>

                                        <div id="kc-info" class="uc1-registration">
                                            <span>${msg("backToLogin")?no_esc} <a href="${url.loginRestartFlowUrl}" class="uc1-link">${msg("doLogIn")}</a></span>
                                        </div>
                                    </div>
                                </div>
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
