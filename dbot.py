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
from datetime import datetime
import pymysql
import pandas as pd

from telegram import (InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove, File)
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
SELECTING_FEATURE, TYPING, PROFILE_VIEW, CAND = map(chr, range(6, 10))
# Meta states
STOPPING, SAVING, SHOWING, KNOWING = map(chr, range(10, 14))
# Shortcut for ConversationHandler.END
END = ConversationHandler.END

# Different constants for this example
(CHOOSING_PROFILE, CHOOSING_COMPANY, VIEWING, APPLY, RESUME, EMAIL, PHONE, NAME, START_OVER, FEATURES,
 CURRENT_FEATURE, CURRENT_LEVEL, REFERER, APPLICATION, PDF, XLS, CLOUD, SPDF, SXLS, SAVING_CLOUD,
 COLLECTING_RESUME, COLLECT_METHOD, SAVING_CLOUD, SAVING_RESUME) = map(chr, range(14, 38))


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
        InlineKeyboardButton(text='Search Requirement', callback_data=str(FIND_PROFILE)),
        InlineKeyboardButton(text='Check Status', callback_data=str(SHOWING)),
    ], [
        InlineKeyboardButton(text='View Saved', callback_data=str(VIEWING)),
        InlineKeyboardButton(text='Done', callback_data=str(END))
    ]]
    keyboard = InlineKeyboardMarkup(buttons)

    # If we're starting over we don't need do send a new message
    #print (context.user_data.get(START_OVER))
    if context.user_data.get(START_OVER):
        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        #update.message.reply_text(text=text, reply_markup=keyboard)
    else:
        update.message.reply_text('Hi')
        update.message.reply_text(text=text, reply_markup=keyboard)

    context.user_data[START_OVER] = False
    return SELECTING_ACTION

def collect_resume(update, context):
    text = ""
    text = text + "\n\n\nYou could choose one of the following ways to upload the resumes of candidate.\n"
    text = text + "\n\nSend PDF: Just send me the pdf of the Candidates' Resumes.\n"
    text = text + "\nSend Sheet: Just send me the excel sheet containing data of the candidates applying.\n"
    text = text + "\nSend Cloud Link: Just send me a cloud link from where I could fetch the resumes for you, Don't forget to give necessary permissions.\n"

    buttons = [[
        InlineKeyboardButton(text='Send PDF', callback_data=str(PDF)),
        InlineKeyboardButton(text='Send Sheet', callback_data=str(XLS))],
        [
        InlineKeyboardButton(text='Send Cloud Link', callback_data=str(CLOUD)),
        InlineKeyboardButton(text='Done', callback_data=str(END))
    ]]

    keyboard = InlineKeyboardMarkup(buttons)

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

    return COLLECT_METHOD



def view(update, context):
    """View Saved Requirements"""
    #text = ""
    sr = pd.read_sql_query("SELECT * FROM SAVEDATA", conn)
    if sr.empty:
        text = "You have not saved any requirements yet!"

    else:
        text = "Here is the list of your saved requirements."



        text = text + "\n\n\nYou could choose one of the following ways to upload the resumes of candidate.\n"
        text = text + "\n\nSend PDF: Just send me the pdf of the Candidates' Resumes.\n"
        text = text + "\nSend Sheet: Just send me the excel sheet containing data of the candidates applying.\n"
        text = text + "\nSend Cloud Link: Just send me a cloud link from where I could fetch the resumes for you, Don't forget to give necessary permissions."

    buttons = [[
        InlineKeyboardButton(text='Send PDF', callback_data=str(PDF)),
        InlineKeyboardButton(text='Send Sheet', callback_data=str(XLS))],
        [
        InlineKeyboardButton(text='Send Cloud Link', callback_data=str(CLOUD)),
        InlineKeyboardButton(text='Done', callback_data=str(END)),
    ]]

    keyboard = InlineKeyboardMarkup(buttons)

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

    return COLLECT_METHOD


def show_data(update, context):
    global chat_id
    chat_id = update.callback_query.message.chat.id
    ud = context.user_data
    #context.user_data[CURRENT_LEVEL] = SELF
    
    candi = pd.read_sql_query("SELECT * FROM CANDIDATE WHERE Referer_id = '{}'".format(chat_id), conn)
    

    text = 'Here is the list of Companies you have appled in, please choose to continue\n\n'
    for id in candi['C_id']:
        c = candi[candi['C_id']==id]['Company'].values[0]
        text = str(text) + str(c)+ '\n'
    
    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text)
    
    return PROFILE_VIEW

def profile_view(update, context):

    global show_company
    show_company = update.message.text
    text = 'Here are the profiles you applied for at '+ show_company + ' company\n\n'
    pro = pd.read_sql_query("SELECT Profile FROM CANDIDATE WHERE Company = '{0}' AND Referer_id='{1}'".format(show_company, chat_id), conn)
    for p in pro['Profile']:
        text = text + str(p) + '\n'

    update.message.reply_text(text)

    return CAND

def cand(update, context):
    ud = context.user_data
    global show_profile
    show_profile = update.message.text
    data = pd.read_sql_query("SELECT * FROM CANDIDATE WHERE Company = '{0}' AND Profile='{1}' AND Referer_id='{2}'".format(show_company, show_profile, chat_id), conn)
    
    text = 'The status of candidates applied for '+show_profile+' profile at '+show_company+' company is as follows\n\n'
    
    for id in data['C_id']:
        st = data[data['C_id']==id]['Status'].values[0]
        if st == 0:
            sta = 'Pending'
        else:
            sta = 'Accepted'
    
    for id in data['C_id']:
        text = str(text) + 'C_ID:'+str(id) + '    ' + 'Date of Application:'+str(data[data['C_id']==id]['Date_of_App'].values[0]) + '   ' + 'Status:'+str(sta) +'\n' + '--------------------------------------------------------------------'

    buttons = [[InlineKeyboardButton(text='Back', callback_data=str(END))]]
    keyboard = InlineKeyboardMarkup(buttons)
    
    #update.callback_query.answer()
    update.message.reply_text(text=text, reply_markup=keyboard)

    ud[START_OVER] = True
    return SHOWING

def save_data(update, context):
    
    ud = context.user_data
    global ref_name, ref_phone, ref_email
    ref_name = ud[FEATURES][NAME]
    ref_phone = ud[FEATURES][PHONE]
    ref_email = ud[FEATURES][EMAIL]
    save_id = ref_email.split("@")[0] + str(req_id)

    try:
        with conn.cursor() as cursor:
            # Create a new record
            sql = "INSERT INTO SAVEDATA VALUES (%s, %s,%s,%s)"
            cursor.execute(sql, (save_id, ref_name, ref_phone, ref_email))

        # connection is not autocommit by default. So you must commit to save
        # your changes.
        conn.commit()
        '''
        with conn.cursor() as cursor:
            # Read a single record
            sql = "SELECT * FROM SAVEDATA"
            cursor.execute(sql)
            result = cursor.fetchone()
            print(result)
        '''
    finally:
        pass
  
    buttons = [[
        InlineKeyboardButton(text='Upload Resume', callback_data=str(RESUME)),
        InlineKeyboardButton(text='Done', callback_data=str(END))
    ]]
    keyboard = InlineKeyboardMarkup(buttons)

    text = "Your requirement has been saved, You may proceed to upload resumes or browse further requirements."

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
    ud[START_OVER] = True
    
    return COLLECTING_RESUME

#Now we collect Resume
def collect_cloud(update,context):
    text = "Great so just send me the link of cloud location to fetch candidates data!"
    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text)

    return SAVING_CLOUD

def save_cloud(update, context):
    cloud_link = update.message.text
    text = "Congratulations, we will fetch the resumes from the cloud and get working with them."
    '''
    try:
        with conn.cursor() as cursor:
            # Create a new record
            sql = "INSERT INTO CANDIDATE VALUES (%s, %s,%s,%s)"
            cursor.execute(sql, (save_id, ref_name, ref_phone, ref_email))

        # connection is not autocommit by default. So you must commit to save
        # your changes.
        conn.commit()
    '''
    buttons = [[
        InlineKeyboardButton(text='Done', callback_data=str(END))
    ]]
    keyboard = InlineKeyboardMarkup(buttons)

    update.message.reply_text(text = text, reply_markup = keyboard)

    return SAVING_CLOUD

def collect_pdf(update, context):
    
    return SAVING_RESUME

def save_pdf(update, context):
    f = File()
    name = f.download()
    return SAVING_RESUME

def collect_xls(update, context):
    return SAVING_RESUME

def save_xls(update, context):
    f = File()
    name = f.download()
    return SAVING_RESUME    


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

def select_profile(update, context):
    """Choose to add a parent or a child."""
    text = 'Please let me know which profile of job are you looking for.\n'
    pro = pd.read_sql_query("SELECT Profile FROM Requirement WHERE Status=0", conn)
    prof = set(list(pro['Profile']))
    for p in prof:
        text = text + "\n"+p

    #buttons = [[
    #    InlineKeyboardButton(text='Back', callback_data=str(END))
    #]]
    #keyboard = InlineKeyboardMarkup(buttons)
    level = update.callback_query.data
    context.user_data[CURRENT_LEVEL] = level


    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text)

    return CHOOSING_PROFILE



def select_company(update, context):
    """Choose to add a parent or a child."""
    global prof_choose
    prof_choose = update.message.text
    #buttons = [[
    #    InlineKeyboardButton(text='Back', callback_data=str(END))
    #]]
    #keyboard = InlineKeyboardMarkup(buttons)

    text = 'Please let me know which company are you interested in.\n'
    com = pd.read_sql_query("SELECT Company FROM Requirement WHERE Profile='{}' AND Status=0".format(prof_choose), conn)
    comp = set(list(com['Company']))
    for c in comp:
        text = str(text) + "\n"+str(c)

    update.message.reply_text(text, reply_markup=ReplyKeyboardRemove())
    
    #update.message.reply_text(text)
    #update.callback_query.answer()
    #update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

    return CHOOSING_COMPANY



def select_rid(update, context):
    """Choose to add a parent or a child."""
    global comp_choose
    comp_choose = update.message.text
    text = 'Tell me the Requirement_id of the requirement you would like to proceed with.\n'
    re = pd.read_sql_query("SELECT * FROM Requirement WHERE Profile = '{0}' AND Company = '{1}' AND Status=0".format(prof_choose, comp_choose), conn)
    text = text + '\n'
    for id in re['R_id']:
        text = str(text) + str(id) + '    ' + str(re[re['R_id']==id]['Location'][0]) + '   ' + str(re[re['R_id']==id]['CTC'][0]) + '\n\n'
    
    #buttons = [[
    #    InlineKeyboardButton(text='Back', callback_data=str(END))
    #]]
    #keyboard = InlineKeyboardMarkup(buttons)

    update.message.reply_text(text, reply_markup=ReplyKeyboardRemove())
    #update.callback_query.answer()
    #update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

    return SELECTING_CHOICE



def select_choice(update, context):
    global req_id
    req_id = update.message.text
    text = ''
    re = pd.read_sql_query("SELECT * FROM Requirement WHERE R_id='{}'".format(req_id), conn)
    text = 'Company: 6' + str(re['Company'].values[0]) + '    Profile: ' + str(re['Profile'].values[0]) + '    Location: ' + str(re['Location'].values[0]) +'\n\nJob Description:\n' + str(re['Description'].values[0]) + '\n\nCTC: ' + str(re['CTC'].values[0])
    #context.user_data[CURRENT_LEVEL] = REFERER

    buttons = [[
        InlineKeyboardButton(text='Apply', callback_data=str(APPLY)),
        InlineKeyboardButton(text='Back', callback_data=str(END))
    ]]
    keyboard = InlineKeyboardMarkup(buttons)

    update.message.reply_text(text = text, reply_markup = keyboard)
    #update.callback_query.answer()
    #update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

    return APPLICATION



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
        InlineKeyboardButton(text='Save', callback_data=str(SAVING)),
    ]]
    keyboard = InlineKeyboardMarkup(buttons)

    # If we collect features for a new person, clear the cache and save the gender
    if not context.user_data.get(START_OVER):
        context.user_data[FEATURES] = {REFERER: update.callback_query.data}
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
    #print(CURRENT_FEATURE)
    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text)

    return TYPING


def save_input(update, context):
    """Save input for feature and return to feature selection."""
    ud = context.user_data
    #if(CURRENT_FEATURE == NAME):
    #    print("bingo")
    #print(ud[CURRENT_FEATURE])
    ud[FEATURES][ud[CURRENT_FEATURE]] = update.message.text
    #print("Run")
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


    #Resume Collection Conversation
    resume_conv = ConversationHandler(allow_reentry=True,
        entry_points=[CallbackQueryHandler(collect_resume, pattern='^'+ str(RESUME) + '$'), CallbackQueryHandler(view, pattern='^' + str(VIEWING) + '$')],

        states={
            COLLECT_METHOD: [CallbackQueryHandler(collect_pdf, pattern = '^' + str(PDF) + '$'),
                             CallbackQueryHandler(collect_xls, pattern = '^' + str(XLS) + '$'),
                             CallbackQueryHandler(collect_cloud, pattern = '^' + str(CLOUD) + '$')
            ],
            SAVING_RESUME: [CallbackQueryHandler(save_pdf, pattern = '^' + str(SPDF) + '$'),
                             CallbackQueryHandler(save_xls, pattern = '^' + str(SXLS) + '$')],
            SAVING_CLOUD: [MessageHandler(Filters.text, save_cloud)]
        },

        fallbacks=[
            CallbackQueryHandler(start, pattern='^' + str(END) + '$'),
            CommandHandler('stop', stop_nested),
            CommandHandler('back', end_describing)
        ],

        map_to_parent={
            # Return to second level menu
            END: CHOOSING_PROFILE,
            # End conversation alltogether
            STOPPING: STOPPING,
        }
    )



    # Set up third level ConversationHandler (collecting features)
    description_conv = ConversationHandler(allow_reentry=True,
        entry_points=[CallbackQueryHandler(select_feature,
                                           pattern='^' + str(APPLY) + '$'), CommandHandler('back', end_describing)],

        states={
            SELECTING_FEATURE: [CallbackQueryHandler(ask_for_input,pattern='^{0}$|^{1}$|^{2}$'.format(str(NAME),
                                                                                str(PHONE), str(EMAIL))), 
                                CallbackQueryHandler(save_data, pattern='^' + str(SAVING) + '$')],
            TYPING: [MessageHandler(Filters.text, save_input)],
            COLLECTING_RESUME: [resume_conv]
        },

        fallbacks=[
            CallbackQueryHandler(end_describing, pattern='^' + str(END) + '$'),
            CommandHandler('stop', stop_nested),
            CommandHandler('back', end_describing)
        ],

        map_to_parent={
            # Return to second level menu
            END: CHOOSING_PROFILE,
            # End conversation alltogether
            STOPPING: STOPPING,
        }
    )

    

    # Set up second level ConversationHandler (adding a person)
    find_profile_conv = ConversationHandler(allow_reentry=True,
        entry_points=[CallbackQueryHandler(select_profile,
                                           pattern='^' + str(FIND_PROFILE) + '$'), CommandHandler('back', end_second_level)],

        states={
            CHOOSING_PROFILE: [MessageHandler(Filters.text, select_company), MessageHandler(Filters.command, select_profile),],
            CHOOSING_COMPANY: [MessageHandler(Filters.text, select_rid), MessageHandler(Filters.command, select_company),],
            SELECTING_CHOICE: [MessageHandler(Filters.text, select_choice), MessageHandler(Filters.command, select_rid,)],
            APPLICATION:[description_conv]
        },  

        fallbacks=[
            CallbackQueryHandler(show_data, pattern='^' + str(SHOWING) + '$'),
            CallbackQueryHandler(end_second_level, pattern='^' + str(END) + '$'),
            CommandHandler('stop', stop_nested),
            CommandHandler('back', end_second_level)
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

    show_data_conv = ConversationHandler(allow_reentry=True,
        entry_points=[CallbackQueryHandler(show_data,
                                           pattern='^' + str(SHOWING) + '$'), CommandHandler('back', end_second_level)],

        states={
            PROFILE_VIEW: [MessageHandler(Filters.text, profile_view), CommandHandler('back', show_data),],
            CAND: [MessageHandler(Filters.text, cand), CommandHandler('back', profile_view),],
        },  

        fallbacks=[
            CallbackQueryHandler(show_data, pattern='^' + str(SHOWING) + '$'),
            CallbackQueryHandler(end_second_level, pattern='^' + str(END) + '$'),
            CommandHandler('stop', stop_nested),
            CommandHandler('back', end_second_level)
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
        entry_points=[CommandHandler('start', start), CommandHandler('back', end_second_level)],

        states={
            SHOWING: [CallbackQueryHandler(start, pattern='^' + str(END) + '$')],
            SELECTING_ACTION: [
                find_profile_conv,
                show_data_conv,
                resume_conv,
                CallbackQueryHandler(end, pattern='^' + str(END) + '$'),
            ],
            DESCRIBING_SELF: [description_conv],

        },

        fallbacks=[CommandHandler('stop', stop)],
    )
    # Because the states of the third level conversation map to the ones of the
    # second level conversation, we need to be a bit hacky about that:
    conv_handler.states[SELECTING_CHOICE] = conv_handler.states[SELECTING_ACTION]
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