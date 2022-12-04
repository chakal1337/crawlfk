#!/usr/bin/python3
import sys
import socket
import time
import requests
import argparse
import json
import threading
import urllib.parse
from urllib.parse import urljoin
from bs4 import BeautifulSoup

debug = False

crawl_depth = 2
threadnum = 25
crawl_queue = []
crawl_data = {}

parser = argparse.ArgumentParser(
 prog = "crawlFk",
 description = "send payloads to forms automagically"
)

parser.add_argument("-t", "--threads")
parser.add_argument("-x", "--depth")
parser.add_argument("-d", "--domain", required=True)
parser.add_argument("-u", "--url", required=True)
parser.add_argument("-p", "--payload", required=True)

args = parser.parse_args()

base_domain = args.domain
base_url = args.url
payload = args.payload
if args.depth: crawl_depth = int(args.depth)
if args.threads: threadnum = int(args.threads)

tlock = threading.Lock()

crawl_queue.append(base_url)
crawl_data[base_url] = {"depth":0, "crawled":0}

def send_form_payload(form_action, form):
 input_names = ["input","textarea","checkbox","select"]
 data = {}
 for input_name in input_names:
  for input in form.find_all(input_name):
   inp_name = input.get("name")
   if not inp_name: continue
   inp_value = input.get("value")
   if inp_value:
    data[inp_name] = inp_value
   else:
    data[inp_name] = payload
 r = requests.post(url=form_action, data=data, allow_redirects=True, timeout=5)
 print("Posted to: {}".format(form_action))

def crawl_proc(url_current, depth=1):
 global crawl_queue, crawl_data
 if depth >= crawl_depth: return
 if crawl_data[url_current]["crawled"] == 1: return
 crawl_data[url_current]["crawled"] = 1
 r = requests.get(url=url_current, allow_redirects=True, timeout=5)
 if r.status_code != 200:
  return
 soup = BeautifulSoup(r.text, "html.parser")
 for link in soup.find_all("a"): 
  link_href = link.get("href")
  if not link_href: continue
  link_href = urljoin(url_current, link_href)
  if not base_domain in link_href: continue
  with tlock:
   if link_href in crawl_data: continue
   crawl_queue.append(link_href)
   crawl_data[link_href] = {"depth":depth, "crawled":0}
  print(link_href)
 for form in soup.find_all("form"):
  form_action = form.get("action")
  if not form_action: continue
  form_action = urljoin(url_current, form_action)
  send_form_payload(form_action, form)

def crawl(): 
 global crawl_queue 
 while len(crawl_queue):
  try:
   with tlock: url_current = crawl_queue.pop(0)
   if debug == 1: print("Crawling {}".format(url_current))
   if crawl_data[url_current]["depth"] >= crawl_depth:
    continue
   crawl_proc(url_current, depth=crawl_data[url_current]["depth"])
  except Exception as error: 
   if debug == 1: print(error)

def main():
 print("Starting...")
 for i in range(threadnum):
  t=threading.Thread(target=crawl)
  t.start()

if __name__ == "__main__":
 main()
