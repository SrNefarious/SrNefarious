#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This program is dedicated to the public domain under the CC0 license.

"""
First, a few callback functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Example of a bot-user conversation using nested ConversationHandlers.
Send /start to initiate the conversation.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import logging

import os
import pymysql
import pandas as pd

from telegram import (InlineKeyboardMarkup, InlineKeyboardButton)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                          ConversationHandler, CallbackQueryHandler)

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

host = os.getenv('MYSQL_HOST')
port = os.getenv('MYSQL_PORT')
user = os.getenv('MYSQL_USER')
password = os.getenv('MYSQL_PASSWORD')
database = os.getenv('MYSQL_DATABASE')

conn = pymysql.connect(
    host=host,
    port=int(3306),
    user="root",
    passwd="root",
    db="Innate",
    charset='utf8mb4')

# State definitions for top level conversation
SELECTING_ACTION, FIND_PROFILE, ADDING_SELF, DESCRIBING_SELF = map(chr, range(4))
# State definitions for second level conversation
SELECTING_LEVEL, SELECTING_CHOICE = map(chr, range(4, 6))
# State definitions for descriptions conversation
SELECTING_FEATURE, TYPING = map(chr, range(6, 8))
# Meta states
STOPPING, SAVING, SHOWING, KNOWING = map(chr, range(8, 12))
# Shortcut for ConversationHandler.END
END = ConversationHandler.END

# Different constants for this example
(CHOOSING_PROFILE, CHOOSING_COMPANY, SELF, APPLY, RESUME, EMAIL, PHONE, NAME, START_OVER, FEATURES,
 CURRENT_FEATURE, CURRENT_LEVEL) = map(chr, range(12, 24))


# Helper
def _name_switcher(level):
    if level == PARENTS:
        return ('Father', 'Mother')
    elif level == CHILDREN:
        return ('Brother', 'Sister')


# Top level conversation callbacks
def start(update, context):
    """Select an action: Adding parent/child or show data."""
    text = 'You may choose to search or apply for a requirement, check status of applications or end the ' \
           'conversation. To abort, simply type /stop.'
    buttons = [[
        InlineKeyboardButton(text='Search for Requirements', callback_data=str(FIND_PROFILE)),
        InlineKeyboardButton(text='Check Status', callback_data=str(SHOWING)),
    ], [
        InlineKeyboardButton(text='Done', callback_data=str(END))
    ]]
    keyboard = InlineKeyboardMarkup(buttons)

    # If we're starting over we don't need do send a new message
    if context.user_data.get(START_OVER):
        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    else:
        update.message.reply_text('Hi')
        update.message.reply_text(text=text, reply_markup=keyboard)

    context.user_data[START_OVER] = False
    return SELECTING_ACTION




def adding_self(update, context):
    """Add information about youself."""
    context.user_data[CURRENT_LEVEL] = SELF
    text = 'Okay, please tell me about yourself.'
    button = InlineKeyboardButton(text='Add info', callback_data=str(MALE))
    keyboard = InlineKeyboardMarkup.from_button(button)

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

    return DESCRIBING_SELF

def show_data(update, context):
    chat_id = update.callback_query.message.chat.id
    ud = context.user_data
    #context.user_data[CURRENT_LEVEL] = SELF
    candi = pd.read_sql_query("SELECT * FROM CANDIDATE WHERE Referer_id = {}".format(chat_id), conn)
    
    text = ''
    for id in candi['C_id']:
        st = candi[candi['C_id']==id]['Status'].values[0]
        if st == 0:
            sta = 'Pending'
        else:
            sta = 'Accepted'

        text = str(text) + str(id) + '  |'   + str(candi[candi['C_id']==id]['Profile'].values[0]) + '  |' + str(candi[candi['C_id']==id]['Company'].values[0])  + '  |' + sta + '\n'

    buttons = [[InlineKeyboardButton(text='Back', callback_data=str(END))]]
    keyboard = InlineKeyboardMarkup(buttons)
    
    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    ud['START_OVER'] = True
    
    return SHOWING

def save_data(update, context):
    """Pretty print gathered data.
    def prettyprint(user_data, level):
        people = user_data.get(level)
        if not people:
            return '\nNo information yet.'

        text = ''
        if level == SELF:
            for person in user_data[level]:
                text += '\nName: {0}, Age: {1}'.format(person.get(NAME, '-'), person.get(AGE, '-'))
        else:
            male, female = _name_switcher(level)

            for person in user_data[level]:
                gender = female if person[GENDER] == FEMALE else male
                text += '\n{0}: Name: {1}, Age: {2}'.format(gender, person.get(NAME, '-'),
                                                            person.get(AGE, '-'))
        return text

    ud = context.user_data
    text = 'Yourself:' + prettyprint(ud, SELF)
    text += '\n\nParents:' + prettyprint(ud, PARENTS)
    text += '\n\nChildren:' + prettyprint(ud, CHILDREN)

    buttons = [[
        InlineKeyboardButton(text='Back', callback_data=str(END))
    ]]
    keyboard = InlineKeyboardMarkup(buttons)

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    ud[START_OVER] = True
    """
    return SAVING
    

def stop(update, context):
    """End Conversation by command."""
    update.message.reply_text('Okay, bye.')

    return END


def end(update, context):
    """End conversation from InlineKeyboardButton."""
    update.callback_query.answer()

    text = 'See you around!'
    update.callback_query.edit_message_text(text=text)

    return END


# Second level conversation callbacks

prof_choose = ''
comp_choose = ''
req_id = ''

def select_profile(update, context):
    """Choose to add a parent or a child."""
    text = 'Please let me know which profile of job are you looking for.\n'
    pro = pd.read_sql_query("SELECT Profile FROM Requirement WHERE Status=0", conn)
    prof = set(list(pro['Profile']))
    for p in prof:
        text = text + "\n"+p

    buttons = [[
        InlineKeyboardButton(text='Back', callback_data=str(END))
    ]]
    keyboard = InlineKeyboardMarkup(buttons)

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

    return CHOOSING_PROFILE

def passing_on_profile(update, context):
    """Save input for feature and return to feature selection."""
    ud = context.user_data
    prof_choose= update.message.text

    #ud[START_OVER] = True

    return select_company(update, context)

def select_company(update, context):
    """Choose to add a parent or a child."""
    #prof_choose = update.message.text
    text = 'Please let me know which company are you interested in.\n'
    com = pd.read_sql_query("SELECT Company FROM Requirement WHERE Profile='{}' AND Status=0".format(prof_choose), conn)
    comp = set(list(com['Company']))
    for c in comp:
        text = str(text) + "\n"+str(c)

    buttons = [[
        InlineKeyboardButton(text='Back', callback_data=str(END))
    ]]
    keyboard = InlineKeyboardMarkup(buttons)

    
    #update.callback_query.answer()
    update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

    return CHOOSING_COMPANY

def passing_on_company(update, context):
    """Save input for feature and return to feature selection."""
    ud = context.user_data
    comp_choose= update.message.text

    #ud[START_OVER] = True

    return select_rid(update, context)

def select_rid(update, context):
    """Choose to add a parent or a child."""
    #comp_choose = update.message.text
    text = 'Tell me the Requirement_id of the requirement you would like to proceed with.\n'
    re = pd.read_sql_query("SELECT * FROM Requirement WHERE Profile = '{0}' AND Company = '{1}' AND Status=0".format(prof_choose,comp_choose), conn)
    
    text = ''
    for id in re['R_id']:
        text = str(text) + str(id) + '    ' + str(re[re['R_id']==id]['Location'][0]) + '   ' + str(re[re['R_id']==id]['CTC'][0]) + '\n\n'
    
    buttons = [[
        InlineKeyboardButton(text='Back', callback_data=str(END))
    ]]
    keyboard = InlineKeyboardMarkup(buttons)

    
    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

    return SELECTING_CHOICE

def passing_on_rid(update, context):
    """Save input for feature and return to feature selection."""
    ud = context.user_data
    req_id= update.message.text

    #ud[START_OVER] = True

    return select_choice(update, context)

def select_choice(update, context):
    #req_id = update.message.text
    text = ''
    re = pd.read_sql_query("SELECT * FROM Requirement WHERE R_id={}".format(req_id), conn)
    text = 'Company:' + str(re['Company']) + '    Profile' + str(re['Profile']) + '    Location' + str(re['Location']) +'\n\nJob Description:\n' + str(re['Description']) + '\nCTC: ' + str(re['CTC'])


    buttons = [[
        InlineKeyboardButton(text='Apply', callback_data=str(APPLY)),
        InlineKeyboardButton(text='Back', callback_data=str(END))
    ]]
    keyboard = InlineKeyboardMarkup(buttons)

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

    return APPLY



def end_second_level(update, context):
    """Return to top level conversation."""
    context.user_data[START_OVER] = True
    start(update, context)

    return END


# Third level callbacks
def select_feature(update, context):
    """Select a feature to update for the person."""
    buttons = [[
        InlineKeyboardButton(text='Name', callback_data=str(NAME)),
        InlineKeyboardButton(text='Phone', callback_data=str(PHONE)),
        InlineKeyboardButton(text='Email', callback_data=str(EMAIL)),
        InlineKeyboardButton(text='Resume', callback_data=str(RESUME)),
        InlineKeyboardButton(text='Save', callback_data=str(SAVING)),
    ]]
    keyboard = InlineKeyboardMarkup(buttons)

    # If we collect features for a new person, clear the cache and save the gender
    if not context.user_data.get(START_OVER):
        context.user_data[FEATURES] = {GENDER: update.callback_query.data}
        text = 'Please select a feature to update.'

        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    # But after we do that, we need to send a new message
    else:
        text = 'Got it! Please select a feature to update.'
        update.message.reply_text(text=text, reply_markup=keyboard)

    context.user_data[START_OVER] = False
    return SELECTING_FEATURE


def ask_for_input(update, context):
    """Prompt user to input data for selected feature."""
    context.user_data[CURRENT_FEATURE] = update.callback_query.data
    text = 'Okay, tell me.'

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text)

    return TYPING


def save_input(update, context):
    """Save input for feature and return to feature selection."""
    ud = context.user_data
    ud[FEATURES][ud[CURRENT_FEATURE]] = update.message.text

    ud[START_OVER] = True

    return select_feature(update, context)


def end_describing(update, context):
    """End gathering of features and return to parent conversation."""
    ud = context.user_data
    level = ud[CURRENT_LEVEL]
    if not ud.get(level):
        ud[level] = []
    ud[level].append(ud[FEATURES])

    # Print upper level menu
    if level == SELF:
        ud[START_OVER] = True
        start(update, context)
    else:
        select_profile(update, context)

    return END


def stop_nested(update, context):
    """Completely end conversation from within nested conversation."""
    update.message.reply_text('Okay, bye.')

    return STOPPING


# Error handler
def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater("907683969:AAF846LM-skVJx5KAl0HQ3MbKyeLAUaZ_wc",  use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Set up third level ConversationHandler (collecting features)
    description_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(select_feature,
                                           pattern='^' + str(APPLY) + '$')],

        states={
            SELECTING_FEATURE: [CallbackQueryHandler(ask_for_input,
                                                     pattern='^(?!' + str(END) + ').*$')],
            TYPING: [MessageHandler(Filters.text, save_input)],
        },

        fallbacks=[
            CallbackQueryHandler(end_describing, pattern='^' + str(END) + '$'),
            CommandHandler('stop', stop_nested)
        ],

        map_to_parent={
            # Return to second level menu
            END: SELECTING_LEVEL,
            # End conversation alltogether
            STOPPING: STOPPING,
        }
    )

    find_req_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(select_choice)],

        states={
            APPLY: [description_conv]
        },

        fallbacks=[
            CallbackQueryHandler(show_data, pattern='^' + str(SHOWING) + '$'),
            CallbackQueryHandler(end_second_level, pattern='^' + str(END) + '$'),
            CommandHandler('stop', stop_nested)
        ],

        map_to_parent={
            # After SHOWING data return to top level menu
            SHOWING: SHOWING,
            # Return to top level menu
            END: SELECTING_ACTION,
            # End conversation alltogether
            STOPPING: END,
        }
    )

    find_rid_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(select_rid)],

        states={
            SELECTING_CHOICE: [MessageHandler(Filters.text, passing_on_rid)]
        },

        fallbacks=[
            CallbackQueryHandler(show_data, pattern='^' + str(SHOWING) + '$'),
            CallbackQueryHandler(end_second_level, pattern='^' + str(END) + '$'),
            CommandHandler('stop', stop_nested)
        ],

        map_to_parent={
            # After SHOWING data return to top level menu
            SHOWING: SHOWING,
            # Return to top level menu
            END: SELECTING_ACTION,
            # End conversation alltogether
            STOPPING: END,
        }
    )

    find_company_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(select_company)],

        states={
            CHOOSING_COMPANY: [MessageHandler(Filters.text, passing_on_company)]
        },

        fallbacks=[
            CallbackQueryHandler(show_data, pattern='^' + str(SHOWING) + '$'),
            CallbackQueryHandler(end_second_level, pattern='^' + str(END) + '$'),
            CommandHandler('stop', stop_nested)
        ],

        map_to_parent={
            # After SHOWING data return to top level menu
            SHOWING: SHOWING,
            # Return to top level menu
            END: SELECTING_ACTION,
            # End conversation alltogether
            STOPPING: END,
        }
    )

    # Set up second level ConversationHandler (adding a person)
    find_profile_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(select_profile,
                                           pattern='^' + str(FIND_PROFILE) + '$')],

        states={
            CHOOSING_PROFILE: [MessageHandler(Filters.text, passing_on_profile)]
        },

        fallbacks=[
            CallbackQueryHandler(show_data, pattern='^' + str(SHOWING) + '$'),
            CallbackQueryHandler(end_second_level, pattern='^' + str(END) + '$'),
            CommandHandler('stop', stop_nested)
        ],

        map_to_parent={
            # After SHOWING data return to top level menu
            SHOWING: SHOWING,
            # Return to top level menu
            END: SELECTING_ACTION,
            # End conversation alltogether
            STOPPING: END,
        }
    )

    # Set up top level ConversationHandler (selecting action)
    conv_handler = ConversationHandler(allow_reentry=True,
        entry_points=[CommandHandler('start', start)],

        states={
            SHOWING: [CallbackQueryHandler(start, pattern='^' + str(END) + '$')],
            SELECTING_ACTION: [
                find_profile_conv,
                CallbackQueryHandler(show_data, pattern='^' + str(SHOWING) + '$'),
                CallbackQueryHandler(adding_self, pattern='^' + str(ADDING_SELF) + '$'),
                CallbackQueryHandler(end, pattern='^' + str(END) + '$'),
            ],
            DESCRIBING_SELF: [description_conv],

        },

        fallbacks=[CommandHandler('stop', stop)],
    )
    # Because the states of the third level conversation map to the ones of the
    # second level conversation, we need to be a bit hacky about that:
    conv_handler.states[CHOOSING_PROFILE] = conv_handler.states[SELECTING_ACTION]
    conv_handler.states[STOPPING] = conv_handler.entry_points

    dp.add_handler(conv_handler)

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()