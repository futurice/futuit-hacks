from gdata.client import GDClient
from gdata.client import CaptchaChallenge
from gdata.client import BadAuthentication
from gdata.gauth import ClientLoginToken
from gdata.gauth import OAuth2Token
from gdata.gauth import TwoLeggedOAuthHmacToken

import os.path
import logging
import ConfigParser
import getpass

CONFIG_SECTION = "gdata"
CONFIG_ITEM_TOKEN_TYPE = "token_type"

CONFIG_TOKEN_TYPE_LOGIN = "login"
CONFIG_ITEM_SERVICE = "service"
CONFIG_ITEM_ACCOUNT_TYPE = "account_type"
CONFIG_ITEM_USER_TOKEN = "user_auth_token"

CONFIG_TOKEN_TYPE_OAUTH2 = "oauth2"
CONFIG_ITEM_SCOPES = "scopes"
CONFIG_ITEM_CLIENT_ID = "client_id"
CONFIG_ITEM_CLIENT_SECRET = "client_secret"
CONFIG_ITEM_ACCESS_TOKEN = "access_token"
CONFIG_ITEM_REFRESH_TOKEN = "refresh_token"

CONFIG_TOKEN_TYPE_DOMAIN = "domain"
CONFIG_ITEM_CONSUMER_KEY = "consumer_key"
CONFIG_ITEM_CONSUMER_SECRET = "consumer_secret"

def obtain_domain_token(token_file, requestor_id=None):
    """Returns a gdata.gaut.TwoLeggedOAuthHmacToken. Reads the token from token_file.

    Args:
        token_file: Name of a file that stores the domain token data.
        requestor_id: The email of the user you want to access as. You can later change
                      this by changing the requestor_id property of the returned object.
    Raises:
        InvalidDomainTokenFile: When no valid token was found from token_file.
    """
    if not isinstance(token_file, basestring):
        raise AttributeError("token_file must be a string")

    config = ConfigParser.RawConfigParser()
    if not os.path.exists(token_file): raise InvalidDomainTokenFile()
    config.read(token_file)
    if not config.has_section(CONFIG_SECTION): raise InvalidDomainTokenFile()

    if  config.has_option(CONFIG_SECTION, CONFIG_ITEM_TOKEN_TYPE) and \
        config.has_option(CONFIG_SECTION, CONFIG_ITEM_CONSUMER_KEY) and \
        config.has_option(CONFIG_SECTION, CONFIG_ITEM_CONSUMER_SECRET):

        if config.get(CONFIG_SECTION, CONFIG_ITEM_TOKEN_TYPE) != CONFIG_TOKEN_TYPE_DOMAIN:
            logging.error("Stored token is of a different type.")
        else:
            token = TwoLeggedOAuthHmacToken(
                requestor_id=requestor_id,
                consumer_key=config.get(CONFIG_SECTION, CONFIG_ITEM_CONSUMER_KEY),
                consumer_secret=config.get(CONFIG_SECTION, CONFIG_ITEM_CONSUMER_SECRET))
            return token

    raise InvalidDomainTokenFile()
    
def obtain_oauth2_token(token_file, scopes, client_id, client_secret, user_agent, reauth=False, batch=True):
    """Returns a gdata.gaut.OAuth2Token. Reads the token from token_file if available. Otherwise,
    asks the user interactively to visit an URL and stores the obtained token to token_file.

    Args:
        token_file: Name of a file that stores the token once authorized.
        scopes: The requested scopes (space-separated list of URLs) that this authorization can access.
        client_id: The OAuth2 client ID from API Console.
        client_secret: The OAuth2 client secret from API Console.
        user_agent: Application identifier. Should take the form companyName-applicationName-versionID. E.g. Futurice-AppName-1
        reauth: Force user reauthorization to obtain a new token.
        batch: Consider need to interactive reauthorization an error.
    Raises:
        ReAuthRequiredError: if reauthoriztion is needed but batch is True.
    """
    if not isinstance(token_file, basestring):
        raise AttributeError("token_file must be a string")

    config = ConfigParser.RawConfigParser()
    if os.path.exists(token_file): config.read(token_file)
    if not config.has_section(CONFIG_SECTION): config.add_section(CONFIG_SECTION)
    token = None

    if  not reauth and \
        config.has_option(CONFIG_SECTION, CONFIG_ITEM_TOKEN_TYPE) and \
        config.has_option(CONFIG_SECTION, CONFIG_ITEM_SCOPES) and \
        config.has_option(CONFIG_SECTION, CONFIG_ITEM_CLIENT_ID) and \
        config.has_option(CONFIG_SECTION, CONFIG_ITEM_CLIENT_SECRET) and \
        config.has_option(CONFIG_SECTION, CONFIG_ITEM_ACCESS_TOKEN) and \
        config.has_option(CONFIG_SECTION, CONFIG_ITEM_REFRESH_TOKEN):

        if config.get(CONFIG_SECTION, CONFIG_ITEM_TOKEN_TYPE) != CONFIG_TOKEN_TYPE_OAUTH2:
            logging.warn("Stored token was of a different type.")
        elif config.get(CONFIG_SECTION, CONFIG_ITEM_SCOPES) != scopes:
            logging.warn("Stored OAuth2 token had a different scope.")
        elif config.get(CONFIG_SECTION, CONFIG_ITEM_CLIENT_ID) != client_id:
            logging.warn("Stored OAuth2 token had a different Client ID.")
        elif config.get(CONFIG_SECTION, CONFIG_ITEM_CLIENT_SECRET) != client_secret:
            logging.warn("Stored OAuth2 token had a different Client Secret.")
        else:
            return OAuth2Token(
                client_id=client_id, client_secret=client_secret, scope=scopes, user_agent=user_agent,
                access_token=config.get(CONFIG_SECTION, CONFIG_ITEM_ACCESS_TOKEN),
                refresh_token=config.get(CONFIG_SECTION, CONFIG_ITEM_REFRESH_TOKEN))

    # Re-auth required
    if batch: raise ReAuthRequiredError()

    token = OAuth2Token(client_id=client_id, client_secret=client_secret, scope=scopes, user_agent=user_agent)
    authorize_code = converse_oauth2(token.generate_authorize_url())
    token.get_access_token(authorize_code)

    config.set(CONFIG_SECTION, CONFIG_ITEM_TOKEN_TYPE, CONFIG_TOKEN_TYPE_OAUTH2)
    config.set(CONFIG_SECTION, CONFIG_ITEM_SCOPES, scopes)
    config.set(CONFIG_SECTION, CONFIG_ITEM_CLIENT_ID, client_id)
    config.set(CONFIG_SECTION, CONFIG_ITEM_CLIENT_SECRET, client_secret)
    config.set(CONFIG_SECTION, CONFIG_ITEM_ACCESS_TOKEN, token.access_token)
    config.set(CONFIG_SECTION, CONFIG_ITEM_REFRESH_TOKEN, token.refresh_token)
    config.write(open(token_file, "w"))

    logging.debug("Successfully obtained and saved an authorization token.")
    return token

def obtain_login_token(token_file, service, user_agent, account_type="HOSTED", reauth=False, batch=True):
    """Returns a gdata.gaut.ClientLoginToken. Reads the saved token from token_file if available. Otherwise,
    asks the user interactively for email and password and stores the obtained token to token_file.

    Args:
        token_file: Name of a file that stores the token once authorized.
        service: The service code string (comma-separated list of two-letter codes) that this authorization can access.
        user_agent: Application identifier. Should take the form companyName-applicationName-versionID. E.g. Futurice-AppName-1
        account_type: Defaults to HOSTED.
        reauth: Force user reauthorization to obtain a new token.
        batch: Consider need to interactive reauthorization an error.
    Raises:
        ReAuthRequiredError: if reauthoriztion is needed but batch is True.
    """
    if not isinstance(token_file, basestring):
        raise AttributeError("token_file must be a string")

    config = ConfigParser.RawConfigParser()
    if os.path.exists(token_file): config.read(token_file)
    if not config.has_section(CONFIG_SECTION): config.add_section(CONFIG_SECTION)

    if  not reauth and \
        config.has_option(CONFIG_SECTION, CONFIG_ITEM_TOKEN_TYPE) and \
        config.has_option(CONFIG_SECTION, CONFIG_ITEM_SERVICE) and \
        config.has_option(CONFIG_SECTION, CONFIG_ITEM_ACCOUNT_TYPE) and \
        config.has_option(CONFIG_SECTION, CONFIG_ITEM_USER_TOKEN):

        if config.get(CONFIG_SECTION, CONFIG_TOKEN_TYPE) != CONFIG_TOKEN_TYPE_LOGIN:
            logging.warn("Stored token was of a different type.")
        elif config.get(CONFIG_SECTION, CONFIG_ITEM_SERVICE) != service:
            logging.warn("Stored user token was for a different service.")
        elif config.get(CONFIG_SECTION, CONFIG_ITEM_ACCOUNT_TYPE) != account_type:
            logging.warn("Stored user token was for a different account type.")
        else:
            return ClientLoginToken(config.get(CONFIG_SECTION, CONFIG_ITEM_USER_TOKEN))

    # Re-auth required
    if batch: raise ReAuthRequiredError()
    
    token = None
    client = GDClient()
        
    (email, passwd) = converse_credentials()
    (captcha_token, captcha_response) = None, None

    while True:
        try:
            if not captcha_token:
                token = client.client_login(email=email, password=passwd, source=user_agent, service=service, account_type=account_type)
            else:
                token = client.client_login(
                    email=email, password=passwd, source=user_agent, service=service, account_type=account_type,
                    captcha_token=captcha_token, captcha_response=captcha_response)
            break
        except CaptchaChallenge as challenge:
            captcha_token = challenge.captcha_token
            captcha_response = converse_captcha(challenge.captcha_url)
        except BadAuthentication:
            (email, passwd) = converse_credentials(True)

    del email, passwd, captcha_token, captcha_response

    config.set(CONFIG_SECTION, CONFIG_ITEM_TOKEN_TYPE, CONFIG_TOKEN_TYPE_LOGIN)
    config.set(CONFIG_SECTION, CONFIG_ITEM_SERVICE, service)
    config.set(CONFIG_SECTION, CONFIG_ITEM_ACCOUNT_TYPE, account_type)
    config.set(CONFIG_SECTION, CONFIG_ITEM_USER_TOKEN, token.token_string)
    config.write(open(token_file, "w"))

    logging.debug("Successfully obtained and saved an authorization token.")
    return token

def converse_oauth2(url):
    logging.debug("Interactive OAuth2 initiated")

    print "Interactive authorization. Please authrorize this application by visiting the following page:"
    print "\t%s" % url
    return raw_input("The verification code is: ")

def converse_credentials(last_failed=False):
    logging.debug("Interactive login initiated")
    
    if last_failed:
        print "Bad login. Check email and password."

    print "Interactive authorization. Please enter your login details."
    user = raw_input("Google Account email: ")

    return (user, getpass.getpass())

def converse_captcha(url):
    logging.debug("Interactive CAPTCHA initiated")
    
    print "You must prove that you are human. Please view the following image:"
    print "\t%s" % url
    return raw_input("The image reads: ")

class ReAuthRequiredError(Exception):
    """Raised when an interactive authorization would be needed, but batch mode was specified."""
    pass
class InvalidDomainTokenFile(Exception):
    """Raised when invalid domain token file is used."""
    pass
