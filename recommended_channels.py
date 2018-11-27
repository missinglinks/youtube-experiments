import json
import requests
import os
import click
import networkx as nx

from datetime import datetime
from tqdm import tqdm
from collections import defaultdict, Counter
from apiclient.discovery import build
from bs4 import BeautifulSoup

from config import YOUTUBE_API_KEY

YOUTUBE_VIDEO = "https://www.youtube.com/watch?v={id}"
YOUTUBE_UPLOADS = "https://www.youtube.com/{}/videos?sort=dd&flow=grid" 
YOUTUBE_EMBED = "https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={}"

def normalize(slug):
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    if "channel/" in slug:
        channel_id = slug.replace("channel/", "").strip()
    elif "user/" in slug:
        channel_id = get_channel_id(yt, slug.replace("user/", "").strip())
    else:
        print("invalid channel slug")
        return None

def get_latest_vids(slug):
    resp = requests.get(YOUTUBE_UPLOADS.format(slug))
    soup = BeautifulSoup(resp.text, "html.parser")
    videos = []
    for a in soup.find_all("a", {"class": "yt-uix-tile-link"}):
        title = a.text
        id_ = a["href"][9:]
        videos.append(id_)
    return videos

def get_channel_name(video_id):
    resp = requests.get(YOUTUBE_EMBED.format(video_id))
    try:
        data = resp.json()
        return data["author_name"], data["title"]
    except:
        print(video_id)


def get_video_ids(video_id):
    """
    extracts ids from recommended video list on a videos youtube page
    """
    resp = requests.get(YOUTUBE_VIDEO.format(id=video_id))
    soup = BeautifulSoup(resp.text, "html.parser")
    video_ids = set()

    for li in soup.find_all("li", {"class":"related-list-item"}):
        link = li.find("a")["href"]
        video_id = link.split("=")[-1].split("&")[0]
        video_ids.add(video_id)
    return list(video_ids)

def iter_video_ids(video_id, precision=50, n=30):
    rv = []
    c = Counter()
    vids = set()
    for i in tqdm(range(precision)):
        s = set(get_video_ids(video_id))
        c.update(s)
        #print(i, " new videos: ", len(s-vids), " ({})".format(len(vids)))
        vids = vids.union(s)
    print("getting channel names ...")
    for id_, count in tqdm(list(c.most_common(len(c)))[:n]):
        data = get_channel_name(id_)
        if data:
            rv.append( (id_, data, count) )
    return rv

done = []
def build_network(seed, channel, G, depth, precision=30, n=30):
    if depth > 0:
        response = iter_video_ids(seed, precision=precision, n=n)
        for video_id, data, count in response:
            
            if channel != data[0]:
                if G.has_edge(channel, data[0]):
                    G[channel][data[0]]["weight"] += count
                else:
                    G.add_edge(channel, data[0], weight=count)
            
            done.append(seed)
        for video_id, data, count in response:
            if video_id not in done:
                build_network(video_id, data[0], G, depth=depth-1, precision=precision, n=n)

@click.command()
@click.argument("seed")
@click.option("--precision","-p",default=20)
@click.option("--depth", "-d", default=2)
@click.option("-n", default=20)
def recommended_channel_network(seed, precision, depth, n):
    G = nx.DiGraph()

    if "channel" or "user" in seed:
        channel = normalize(seed)
        res = []
        videos = get_latest_vids(seed)
        for i, video in enumerate(videos[:20]):
            print(i, video)
            build_network(video, channel, G, depth=n, precision=precision, n=n)

        network_file = os.path.join("data", "{}_{}.graphml".format(channel, datetime.now().isoformat()[:19].replace(":","_")))
    else:
        channel, title = get_channel_name(seed)
        build_network(seed, channel, G, depth=depth, precision=precision, n=n)

        network_file = os.path.join("data", "{}_{}_{}.graphml".format(channel, title[:30], datetime.now().isoformat()[:19].replace(":","_")))
    nx.write_graphml(G, network_file)

if __name__ == "__main__":
    recommended_channel_network()