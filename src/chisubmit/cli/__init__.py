
#  Copyright (c) 2013-2014, The University of Chicago
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are met:
#
#  - Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
#  - Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
#  - Neither the name of The University of Chicago nor the names of its
#    contributors may be used to endorse or promote products derived from this
#    software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
#  AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
#  IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
#  ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
#  LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#  CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
#  SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
#  INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
#  CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
#  ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
#  POSSIBILITY OF SUCH DAMAGE.

import click
from chisubmit.common import ChisubmitException, CHISUBMIT_FAIL,\
    handle_unexpected_exception, CHISUBMIT_SUCCESS
import sys
from pprint import pprint
from requests.exceptions import HTTPError, ConnectionError
from chisubmit.cli.admin import admin
#from chisubmit.cli.instructor import instructor
#from chisubmit.cli.student import student
#from chisubmit.cli.grader import grader
import getpass
from docutils.utils.math.math2html import URL
from chisubmit.client.requester import BadRequestException
from chisubmit.client.exceptions import UnknownObjectException,\
    ChisubmitRequestException, UnauthorizedException
config = None

import chisubmit.common.log as log
from chisubmit.config import Config
from chisubmit import RELEASE
from chisubmit.client import Chisubmit

SUBCOMMANDS_NO_COURSE = [('course','create')]
SUBCOMMANDS_DONT_SAVE = ['course-create', 'course-install', 'course-generate-distributable', 'gh-token-create', 'shell']

VERBOSE = False
DEBUG = False 

@click.group(name="chisubmit")
@click.option('--api-url', type=str, default=None)
@click.option('--api-key', type=str, default=None)
@click.option('--conf', type=str, default=None)
@click.option('--dir', type=str, default=None)
@click.option('--course', type=str, default=None)
@click.option('--verbose', '-v', is_flag=True)
@click.option('--debug', is_flag=True)
@click.version_option(version=RELEASE)
@click.pass_context
def chisubmit_cmd(ctx, api_url, api_key, conf, dir, course, verbose, debug):
    global VERBOSE, DEBUG
    
    VERBOSE = verbose
    DEBUG = debug
    
    ctx.obj = {}

    config = Config(dir, conf)
    log.init_logging(verbose, debug)

    if api_key is None:
        if config['api-key'] is None:
            raise click.BadParameter("You do not have any chisubmit credentials. Run chisubmit-get-credentials "
                                     "to obtain your credentials or, if you have an api key, use the --api-key "
                                     "option.")
        else:
            api_key = config['api-key']

    if api_url is None:
        api_url = config['api-url']

    client = Chisubmit(api_key, base_url=api_url)

    if course:
        course_specified = True
        course_id = course
    else:
        course_specified = False
        course_id = config['default-course']

    ctx.obj["client"] = client
    ctx.obj["course_specified"] = course_specified
    ctx.obj["course_id"] = course_id
    ctx.obj["config"] = config
    ctx.obj["verbose"] = verbose
    ctx.obj["debug"] = debug

    return CHISUBMIT_SUCCESS


def chisubmit_cmd_wrapper():
    cmd_wrapper(chisubmit_cmd)


def cmd_wrapper(cmd):
    try:
        cmd.main()
    except UnknownObjectException, uoe:
        print
        print "ERROR: There was an error processing this request"
        print
        print "URL: %s" % uoe.url
        print "HTTP method: %s" % uoe.method
        print "Error: Not found (404)"
        if DEBUG:
            print
            uoe.print_debug_info()
    except UnauthorizedException, ue:
        print
        print "ERROR: Your chisubmit credentials are invalid"
        print
        print "URL: %s" % ue.url
        print "HTTP method: %s" % ue.method
        print "Error: Unauthorized (401)"
        if DEBUG:
            print
            uoe.print_debug_info()            
    except BadRequestException, bre:
        print
        print "ERROR: There was an error processing this request"
        print
        print "URL: %s" % bre.url
        print "HTTP method: %s" % bre.method
        print "Error(s):"
        bre.print_errors()
        if DEBUG:
            print
            bre.print_debug_info()
    except ChisubmitRequestException, cre:
        print "ERROR: chisubmit server returned an HTTP error"
        print
        print "URL: %s" % cre.url
        print "HTTP method: %s" % cre.method
        print "Status code: %i" % cre.status
        print "Message: %s" % cre.reason
        if DEBUG:
            print
            bre.print_debug_info()        
    except ConnectionError, ce:
        print "ERROR: Could not connect to chisubmit server"
        print "URL: %s" % ce.request.url
    except ChisubmitException, ce:
        print "ERROR: %s" % ce.message
        if DEBUG:
            ce.print_exception()
        sys.exit(CHISUBMIT_FAIL)
    except Exception, e:
        handle_unexpected_exception()

chisubmit_cmd.add_command(admin)
#chisubmit_cmd.add_command(instructor)
#chisubmit_cmd.add_command(student)
#chisubmit_cmd.add_command(grader)


@click.command(name="chisubmit-get-credentials")
@click.option('--conf', type=str, default=None)
@click.option('--dir', type=str, default=None)
@click.option('--verbose', is_flag=True)
@click.option('--debug', is_flag=True)
@click.option('--api-url', type=str, default=None)
@click.option('--username', prompt='Enter your chisubmit username')
@click.option('--password', prompt='Enter your chisubmit password', hide_input=True)
@click.option('--no-save', is_flag=True)
@click.option('--reset', is_flag=True)
@click.pass_context
def chisubmit_get_credentials_cmd(ctx, conf, dir, verbose, debug, api_url, username, password, no_save, reset):
    global VERBOSE, DEBUG
    
    VERBOSE = verbose
    DEBUG = debug
        
    config = Config(dir, conf)

    if api_url is None:
        api_url = config['api-url']

    if api_url is None:
        print "No server URL specified. Please add it to your chisubmit.conf file"
        print "or use the --url option"
        ctx.exit(CHISUBMIT_FAIL)

    client = Chisubmit(username, password=password, base_url=api_url)

    try:
        token, created = client.get_user_token(reset = reset)
    except UnauthorizedException, ue:
        print "ERROR: Incorrect username/password"
        ctx.exit(CHISUBMIT_FAIL)
    except ConnectionError, ce:
        print "ERROR: Could not connect to chisubmit server"
        print "URL: %s" % api_url
        ctx.exit(CHISUBMIT_FAIL) 

    if token:
        config['api-key'] = token
        if config['api-url'] is None and not no_save:
            config['api-url'] = api_url

        if not no_save:
            config.save()

        if created:
            ttype = "NEW"
        else:
            ttype = "EXISTING"
        
        click.echo("")
        click.echo("Your %s chisubmit access token is: %s" % (ttype, token))
        if not no_save:
            click.echo("")
            click.echo("The token has been stored in your chisubmit configuration file.")
            click.echo("You should now be able to use the chisubmit commands.")
        if reset and created:
            click.echo("")
            click.echo("Your previous chisubmit access token has been cancelled.")
            click.echo("Make sure you run chisubmit-get-credentials on any other")
            click.echo("machines where you are using chisubmit.")
        click.echo("")
    else:
        click.echo("Unable to create token. Incorrect username/password.")

    return CHISUBMIT_SUCCESS

def chisubmit_get_credentials_cmd_wrapper():
    cmd_wrapper(chisubmit_get_credentials_cmd)


from chisubmit.cli.server import server_start, server_initdb

@click.group()
@click.option('--conf', type=str, default=None)
@click.option('--dir', type=str, default=None)
@click.option('--verbose', '-v', is_flag=True)
@click.option('--debug', is_flag=True)
@click.version_option(version=RELEASE)
@click.pass_context
def chisubmit_server_cmd(ctx, conf, dir, verbose, debug):
    ctx.obj = {}

    config = Config(dir, conf)
    log.init_logging(verbose, debug)
    
    ctx.obj["config"] = config
        
    return CHISUBMIT_SUCCESS


chisubmit_server_cmd.add_command(server_start)
chisubmit_server_cmd.add_command(server_initdb)

