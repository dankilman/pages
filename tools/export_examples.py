from __future__ import print_function

import errno
import importlib
import os
import threading
import time
import tempfile
from contextlib import contextmanager

import click
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from PIL import Image

from awe import page
import examples


@click.group()
def cli():
    pass


base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
output_examples_dir = os.path.join(base_dir, 'published-examples')


def export_setup():
    os.environ.update({'AWE_OFFLINE': '1', 'AWE_SET_GLOBAL': '1'})
    try:
        os.makedirs(output_examples_dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


@cli.command()
def export_examples():
    export_setup()
    for example, config in examples.exported_examples.items():
        print('Processing {}, {}'.format(example, config))
        module = importlib.import_module('examples.{}'.format(example))
        thread = threading.Thread(target=module.main)
        thread.start()
        terminate_after = config.get('terminate_after')
        if terminate_after:
            time.sleep(terminate_after)
            page.global_page.close()
        thread.join(timeout=300)
        with open(os.path.join(output_examples_dir, '{}.html'.format(example)), 'w') as f:
            f.write(page.global_page.export())


@contextmanager
def _driver():
    options = Options()
    options.headless = True
    arguments = ['--incognito', '--private']
    chrome_path = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
    data_dir = os.path.join(tempfile.gettempdir(), 'local-probe-chrome-data')
    options.binary_location = chrome_path
    arguments.append('--user-data-dir={}'.format(data_dir))
    for argument in arguments:
        options.add_argument(argument)
    result = webdriver.Chrome(options=options)
    try:
        result.set_window_size(1600, 1000)
        yield result
    finally:
        result.close()


@cli.command()
def generate_screenshots():
    with _driver() as driver:
        for example, config in examples.exported_examples.items():
            screenshot = config.get('screenshot')
            if not screenshot:
                continue
            print('Processing {}:'.format(example))
            html_path = os.path.join(output_examples_dir, '{}.html'.format(example))
            screenshot_path = os.path.join(output_examples_dir, '{}.png'.format(example))
            print('- get from selenium')
            driver.get('file://{}'.format(html_path))
            print('- sleep 3 seconds')
            time.sleep(3)
            # sanity
            print('- sanity check')
            driver.find_element_by_id('root')
            if example == 'custom_element':
                element = driver.find_elements_by_tag_name('span')[1]
                chain = ActionChains(driver).move_to_element(element)
                print('- custom_element: hover')
                chain.perform()
                print('- custom_element: sleep 3 seconds')
                time.sleep(3)
            print('- save screenshot')
            driver.save_screenshot(screenshot_path)
            left, top, right, bottom = screenshot
            # scale factor of 2
            left, top, right, bottom = left*2, top*2, right*2, bottom*2
            print('- crop and save screenshot')
            image = Image.open(screenshot_path)
            cropped_image = image.crop((left, top, right, bottom))
            cropped_image.save(screenshot_path)


if __name__ == '__main__':
    cli()
