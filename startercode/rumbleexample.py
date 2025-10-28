"""
Author: Laura Kurek
Date: 2024-12-01

Description: Scrape Rumble videos, collect metadata + first-level comments

"""
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import json
import argparse
import time
from datetime import datetime
import pandas as pd
import signal
import sys
import re
import cmd
import os
import threading
from queue import Queue
import random

def check_daily_follow_limit(user, date):
    '''Check how many accounts we have followed for a given account'''
    user = user
    specific_date = date 
    target_date = pd.to_datetime(specific_date).date()
    
    df_status = pd.read_csv('followers_80K_status.csv')
    df_status['followed_on'] = pd.to_datetime(df_status['followed_on'], format='ISO8601')

    count = df_status[
        (df_status['followed_by'] == user) & 
        (df_status['followed_on'].dt.strftime('%Y-%m-%d') == target_date.strftime('%Y-%m-%d'))
    ]
    return count.shape[0]

def add_comment(video, com_indx, user_id, text, likes, replies, low_scored):
    
    try:
        int_likes = int(likes)
    except:
        int_likes = 0
    
    try:
        int_replies = int(replies)
    except:
        int_replies = 0
    
    comment = {
        "comment_index" : com_indx,
        "username": user_id,
        "comment_text": text,
        "num_likes": int_likes,
        "num_replies": int_replies,
        "low_scored" : low_scored
    }
    
    video["comments"].append(comment)
    print(f"Added comment: {comment}")
    return

def convert_to_number(text):
    # Remove any commas if present
    text = text.replace(',', '')
    
    # If it ends with 'K' or 'k'
    if text.upper().endswith('K'):
        # Remove the K and convert to float first
        number = float(text[:-1]) * 1000
        return int(number)
    
    # Otherwise just convert to integer
    return int(text)

def convert_duration_to_seconds(duration_str):
    """
    Convert duration string to seconds.
    Handles both 'HH:MM:SS' and 'MM:SS' formats.
    """
    # Split the time string by ':'
    parts = duration_str.split(':')
    
    if len(parts) == 3:  # HH:MM:SS format
        hours, minutes, seconds = map(int, parts)
        total_seconds = (hours * 3600) + minutes * 60 + seconds
    elif len(parts) == 2:  # MM:SS format
        minutes, seconds = map(int, parts)
        total_seconds = (minutes * 60) + seconds
    else:
        raise ValueError(f"Unexpected duration format: {duration_str}")
        
    return total_seconds

def scrape_video_metadata(driver, wait, video_id, video_url, video_title, video_dur, thumbnail_url):
    '''Navigate to the video page, and collect metadata and comments'''

    print(f'enter scrape_video_metadata()')
    
    #Click the video
    video_element = wait.until(EC.element_to_be_clickable(
        (By.CSS_SELECTOR, f'div[data-video-id="{video_id}"]')
    ))
    video_element.click()
    time.sleep(2)

    wait = WebDriverWait(driver, 10)

    # Extract video source url
    video_element = driver.find_element(By.CSS_SELECTOR, "video")
    video_src = video_element.get_attribute('src')
    print(f'video source url: {video_src}')

    # Extract channel name
    channel_element = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "div.media-by-channel-container a.media-by--a")
    ))
    channel_name = channel_element.get_attribute('href')
    print(f"Channel: {channel_name}")

    time_fail = False
    # Extract video date in streaming format
    try:
        date_element = driver.find_element(By.CSS_SELECTOR, "div.streamed-on > time")
        
        date = date_element.get_attribute('datetime')
        print(f"Date: {date}")
    except:
        print('Stream date not found. Attempting back up')
        time_fail = True
        pass

    # Extract video date in non-streaming format
    if time_fail:
        try:
            date_element2 = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, '.media-description-info-stream-time')
            ))
            date_2 = date_element2.find_element(By.CSS_SELECTOR, 'div[title]')
            date_str = date_2.get_attribute('title')
            date_obj = datetime.strptime(date_str, "%B %d, %Y")
            # Save datetime obj as str formatted (need for JSON output file)
            date = date_obj.strftime('%Y-%m-%d %H:%M:%S')
            print(f"Date (attempt 2) str: {date}")
        except:
            print('Date not found. Continue on')
            date = 'livestream_not_yet_started'
            pass

    # Extract views
    view_element = wait.until(EC.presence_of_element_located(
        (By.CLASS_NAME, "media-description-info-views")
    ))
    views_str = view_element.text
    print(f"Views: {views_str}")
    views = convert_to_number(views_str)

    # Extract upvotes/likes
    upvotes_element = wait.until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, "span[data-js='rumbles_up_votes']")
    ))
    upvotes_count = upvotes_element.text
    print(f"Upvotes: {upvotes_count}")

    # Extract downvotes/dislikes
    downvotes_element = wait.until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, "span[data-js='rumbles_down_votes']")
    ))
    downvotes_count = downvotes_element.text
    print(f"Downvotes: {downvotes_count}")

    # Extract video tags
    tags_data = []
    try:
        tags_container = driver.find_element(By.CSS_SELECTOR, "div.media-description-tags-container")
        
        # Find all tag elements
        tag_elements = tags_container.find_elements(By.CSS_SELECTOR, "a.video-category-tag")
        for tag in tag_elements:
            tags_data.append(tag.text)
        print(f"Found {len(tags_data)} tags: {tags_data}")
        
    except:
        print('Video has no tags')
        pass
    
    # Collect top line description
    try:
        # Extract video description
        description_element = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "p.media-description")
        ))

        description = description_element.text
        print(f"Description: {description}")
    except:
        print('issue collecting top level description')
        description = " "
        pass

    # Collect additional description if applicable 
    # [this works without having to click the 'Show More' button]
    try:
        
        button = driver.find_element(By.CSS_SELECTOR, "button.media-description--show-button")
        print(f'button: {button}')

        extended_desc_elements = wait.until(EC.presence_of_all_elements_located(
            (By.XPATH, "//p[@class='media-description media-description--more']")
        ))

        # Extract text from each description element
        extended_descriptions = []
        for element in extended_desc_elements:
            text = element.get_attribute('textContent')
            if text:  # Only add non-empty paragraphs
                extended_descriptions.append(text)
        print(f'desc 2: {extended_descriptions}')
        description2 = extended_descriptions

    except:
        print('Issue collecting additional video description, continue on')
        description2 = []
        pass
    
    # Extract number of comments
    comments_element = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "div.comments-header h3.comment-count")
    ))
    comment_number_str = comments_element.text
    
    print(f"Comments: {comment_number_str}")
    comment_number = int(comment_number_str.split()[0])  # Split on whitespace and take first element
    
    # Convert duration to seconds
    video_dur_sec = convert_duration_to_seconds(video_dur)
    
    # Save video data here
    cur_video = {
        "video_id" : video_id,
        "video_url" : video_url,
        "video_title" : video_title,
        "video_duration" : video_dur,
        "video_duration_s" : video_dur_sec,
        "video_thumbnail_url" : thumbnail_url,
        "video_source_url" : video_src,
        "channel_name" : channel_name,
        "video_date" : date,
        "video_views" : views,
        "upvotes_count" : int(upvotes_count),
        "downvotes_count" : int(downvotes_count),
        "video_description" : description,
        "video_description_cont" : description2,
        "video_tags" : tags_data,
        "video_comment_number" : comment_number,
        "comments" : [] 
    }
    
    # Try to extract video comments
    if comment_number > 0:
        try:
            # Extract comments
            comments_section = wait.until(EC.presence_of_element_located(
                (By.CLASS_NAME, "comments-1")
            ))
            # Find first comment
            comment_first = comments_section.find_elements(By.CSS_SELECTOR, ".comment-item.comment-item-first")
            
            # Find remaining comments
            comment_items = comments_section.find_elements(By.XPATH, "//li[@class='comment-item'][not(ancestor::div[@class='comment-replies' or @class='comments-2'])]")
            comment_items.insert(0, comment_first[0])
            
            # Extract comment attributes
            for com_indx, item in enumerate(comment_items):
                try:
                    low_scored = False
                    username = item.get_attribute('data-username')
                    #comment_text = item.find_element(By.CLASS_NAME, "comment-text").text
                    # The below line allows us to get all comments for a page without having to click 'show more'
                    comment_text = item.find_element(By.CLASS_NAME, "comment-text").get_attribute('textContent').strip()
                    num_likes = item.find_element(By.CLASS_NAME, "rumbles-count").text
                    num_replies = item.get_attribute('data-num-replies')

                    try:
                        item.find_element(By.CLASS_NAME, "show-comment-text")
                        low_scored = True
                    except:
                        low_scored = False
                        pass
                    # Adding comment to video dictionary item
                    add_comment(cur_video, com_indx, username, comment_text, num_likes, num_replies, low_scored)
                    
                except Exception as e:
                    print(f"For {com_indx} -- error extracting comment:") #{str(e)}")
                    continue

        except Exception as e:
            print(f'Error extracting video comments')
    
    return cur_video

def triage_video(i, video_id, videos_db, driver, wait, page_num):
    '''Inspect current video in thumbnail grib and determine if we need to scrape it'''
    print(f'enter triage_video()')
    video_scraped = 0
    try:
        # Identify current video using video_id    
        video_element = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, f'div[data-video-id="{video_id}"]')
        ))

        # Scroll video element into view before clicking
        driver.execute_script("arguments[0].scrollIntoView(true);", video_element)
        time.sleep(1)  # Brief pause to allow smooth scrolling
        
        # If we have already scraped this video, continue on
        if video_id in videos_db:
            print(f'Video {video_id} collected already\n')
            
        # If we have not scraped this video, collect data
        else:
            # Extract video metadata from thumbnail
            link = video_element.find_element(By.CSS_SELECTOR, 'a.videostream__link')
            href = link.get_attribute('href')
            title = video_element.find_element(By.CSS_SELECTOR, 'h3.thumbnail__title').text
            thumbnail = video_element.find_element(By.CSS_SELECTOR, 'img.thumbnail__image')
            thumbnail_url = thumbnail.get_attribute('src')
            print(f'thumbnail url: {thumbnail_url}')

            try:
                duration = video_element.find_element(By.CSS_SELECTOR, '.videostream__badge.videostream__status.videostream__status--duration').text
            except:
                duration = "00:00"
            
            print(f"Pg: {page_num} <> Indx: {i} <> Video ID: {video_id} <> title: {title}")
            print(f"Duration: {duration} <> Link: {href}")
            
            # Navigate to video page itself, and collect remaining metadata
            cur_video = scrape_video_metadata(driver, wait, video_id, href, title, duration, thumbnail_url)
            videos_db[video_id] = cur_video
            print(f"Newly scraped video has {len(videos_db[video_id]['comments'])} comments\n")
            video_scraped = 1

            # Navigate back to the grid
            driver.back()
    
    # Level 2 Except: Locate and click next video
    except Exception as e:
        print(f"Error processing video {i+1}: {str(e)}")
        # Save out a backup version of video_db to avoid losing data in the event of an error
        timestamp_str = pd.Timestamp.now().strftime('%Y-%m-%d_%H-%M-%S') # Create timestamped filename
        filename_out = f'./z_archived_rumble/rumble_MLChristiansen_videos_crash_{timestamp_str}.json'
        with open(filename_out, 'w') as dest_file:
            json.dump(videos_db, dest_file, indent=2)
    
    return video_scraped


class CommandLineInterface(cmd.Cmd):
    def __init__(self, browser_controller, **kwargs):
        super().__init__()
        self.browser = browser_controller
        self.prompt = 'browser> '
        self.custom_vars = kwargs
        #self.following_account = following_account
        
    def do_r(self, arg):
        """Scrape data from Rumble videos"""
        break_on = False
        test_break_vid = 26
        test_break_page = 2

        channel_name = self.custom_vars.get('channel')
        #channel_name = 'MLChristiansen' #'TENETmedia' #'MLChristiansen'

        # Load in json library
        filepath = f'rumble_{channel_name}_videos.json'
        if os.path.exists(filepath):
            with open(filepath, 'r') as source_file:
                videoz = json.load(source_file)
            
            timestamp_str = pd.Timestamp.now().strftime('%Y-%m-%d_%H-%M-%S') # Create timestamped filename
            filename_out = f'./z_archived_rumble/rumble_{channel_name}_videos_{timestamp_str}.json'
            with open(filename_out, 'w') as dest_file:
                json.dump(videoz, dest_file, indent=2)
        
            videos_db = videoz
        else:
            videos_db = {}

        # Set up Chrome driver
        driver = self.browser.driver
        url = f'https://rumble.com/c/{channel_name}'
        driver.get(url)
        #driver.get("https://rumble.com/c/TENETmedia")
        

        # Attempt to collect video metadata for all videos in a channel
        try:
            page_num = 1
            videos_scraped = 0
            while True:
                
                print(f'Page {page_num} of channel {channel_name} | Videos collected: {len(videos_db)}')

                wait = WebDriverWait(driver, 10)

                # Locate video thumbnail grid
                grid = wait.until(EC.presence_of_element_located(
                    (By.CLASS_NAME, "thumbnail__grid")
                ))
                video_items = grid.find_elements(By.CLASS_NAME, "thumbnail__grid--item")
                video_count = len(video_items)
                print(f'On page {page_num}, there are {video_count} videos.')

                if break_on:
                    if page_num >= test_break_page: # TESTING BREAK
                        print(f'Reached page 2')
                        break
                
                # Extract video IDs from each item
                video_ids = [item.get_attribute('data-video-id') for item in video_items]
                
                # Loop through video positions
                for i, video_id in enumerate(video_ids, 1):

                    if videos_scraped >= 1:  # Stop after 1 video
                        print("Reached 1 video, stopping early.")
                        break
                    
                    # if break_on:
                    #     if i >= test_break_vid:
                    #     #if videos_scraped >= test_break_vid: # TESTING BREAK
                    #         print(f'Break for testing purposes')
                    #         break
                    
                    video_s = triage_video(i, video_id, videos_db, driver, wait, page_num)
                    videos_scraped += video_s

                # Save out the video_db, overwrite existing json file
                filename_out = f'rumble_{channel_name}_videos.json'
                with open(filename_out, 'w') as dest_file:
                    json.dump(videos_db, dest_file, indent=2)
                
                timestamp_str = pd.Timestamp.now().strftime('%Y-%m-%d_%H-%M-%S') # Create timestamped filename
                filename_out = f'./z_archived_rumble/rumble_{channel_name}_videos_{timestamp_str}.json'
                with open(filename_out, 'w') as dest_file:
                    json.dump(videos_db, dest_file, indent=2)

                # Read in updated video_db for next round
                with open(filepath, 'r') as source_file:
                    videos_db = json.load(source_file)    

                print(f'Completed data collection for page {page_num}')

                # Try navigate to next page
                try:
                    # Locate the next button at the bottom of the page
                    next_button = driver.find_element(By.CSS_SELECTOR, ".paginator--li.paginator--li--next")

                    if not next_button:
                        print("Reached last page - no next button found")
                        break
                    
                    #Scroll video element into view and clik
                    driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                    time.sleep(1)
                    next_button.click()
                    
                    # Wait for page to load
                    time.sleep(2)
                    page_num += 1
                
                except NoSuchElementException:
                    print("No more pages found")
                    break
                
                if videos_scraped >= 1:
                    break
                 
        # Top level except: Open Tenet channel page
        except Exception as e:
            print(f"The exception is {str(e)}")
        
    def do_q(self, arg):
        """Quit the browser and exit"""
        self.browser.quit_browser()
        return True
    
    def do_status(self, arg):
        """Check if browser is running"""
        status = "running" if self.browser.driver else "not running"
        print(f"Browser is {status}")

class BrowserController:
    def __init__(self, profile=None):
        self.driver = None
        self.profile = profile
        self.running = True
        self.command_thread = None
        
        # Set up signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
    
    def get_chrome_options(self):
        """Set up Chrome options"""
        options = Options()
        
        # Add profile if specified
        if self.profile:
            options.add_argument(f'--user-data-dir={self.profile}')
        # Disable images and plugins
        options.add_argument("--blink-settings=imagesEnabled=false")
        options.add_argument("--disable-plugins")
        
        return options
    
    def start_browser(self):
        """Initialize and start the browser with specified options"""
        options = self.get_chrome_options()
        self.driver = webdriver.Chrome(options=options)
        return self.driver
    
    def quit_browser(self):
        """Safely quit the browser"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            print("\nBrowser closed successfully")
            self.running = False
    
    def signal_handler(self, signum, frame):
        """Handle Ctrl+C signal"""
        print("\nCtrl+C detected. Closing browser...")
        self.quit_browser()
        sys.exit(0)
    
    def start_command_interface(self, **kwargs):
        """Start the command line interface with variables"""
        CommandLineInterface(self, **kwargs).cmdloop()

def main():
    
    parser = argparse.ArgumentParser(description='Scrape videos from a Rumble channel')
    parser.add_argument('-bot', '--bot', type=int, required=False, help='Bot account to use')
    parser.add_argument('-flw', '--flw', type=int, required=False, help='Number of follows to make')
    parser.add_argument('-chnl', '--chnl', type=str, required=True, help='Rumble channel to scrape')
    args = parser.parse_args()
    #main(args.bot)

    # with open('bots.json', 'r') as f:
    #     data = json.load(f)
    
    # channel_name = args.chnl
    
    # # For now - hard code Chrome profile Chris (5), which has a Rumble login
    # chrome_profile = data[str(5)]['chrome_profile']
    chrome_profile = None
    # following_account = data[str(5)]['username']
    accounts_to_follow = args.flw
    specific_date = "2024-11-19"
    follow_limit = 110
        
    browser = BrowserController(profile=chrome_profile)


    try:
        
        driver = browser.start_browser()
        
        # Your automation code here
        print(f'opening browser')
        driver.get("https://bbc.com")
        
        # Example: Wait for user input to quit
        print("Browser is running. Press Ctrl+C to quit...")
        
        variables = {
            'following_account': following_account,
            'accounts_to_follow': accounts_to_follow,
            'specific_date': specific_date,
            'follow_limit': follow_limit,
            'channel' : channel_name
        }

        browser.start_command_interface(**variables)

        while browser.running:
            time.sleep(1)
        
    except Exception as e:
        print(f"An error occurred: {e}")
    
    finally:
        input("Press Enter to exit...")
        browser.quit_browser()

if __name__ == "__main__":
    main()


