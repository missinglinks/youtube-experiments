import requests
import csv
import json
import click
from bs4 import BeautifulSoup
from apiclient.discovery import build
from collections import Counter
from tqdm import tqdm
from config import YOUTUBE_API_KEY
from datetime import datetime


YOUTUBE_VIDEO = "https://www.youtube.com/watch?v={id}"
YOUTUBE_UPLOADS = "https://www.youtube.com/{}/videos?sort=dd&flow=grid" 
YOUTUBE_EMBED = "https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={}"

yt = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


def api_video(video_id):
    meta = yt.videos().list(
        id=video_id,
        part="id,snippet"
    ).execute()    
    return meta["items"][0]


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

def six_degrees(video_id, n=6):
    trail = []
    for i in tqdm(range(n)):
        videos = []
        videos = get_video_ids(video_id)
        try:
            data = api_video(videos[0])
            channel = data["snippet"]["channelId"]
            title = data["snippet"]["channelTitle"]
            trail.append( (channel, title, videos[0], video_id) )
            video_id = videos[0]
        except:
            print(i, video_id) 
    if len(trail) == n:
        return trail
    else:
        return None

def get_title_channel(video_id):
    meta = api_video(video_id)
    channel = meta["snippet"]["channelTitle"]
    title = meta["snippet"]["title"]
    return title, channel

def get_trails(video_id, n=200):
    trails = []
    for i in range(n):
        trail = six_degrees(video_id)
        if trail:
            trails.append(trail)

        title, channel = get_title_channel(video_id)
        
        payload = {
            "video_id": video_id, 
            "video_title": title, 
            "channel": channel,
            "retrieved_at": datetime.now().isoformat(),
            "total_iterations": n,
            "successfull_iterations": len(trails),
            "trails": trails
        }
    
    return payload

@click.command()
@click.argument("video_id")
@click.option("-n", default=20)
def autoplay_experiment(video_id, n):
    #VIDEO = "B49yZYQyl-M"
    data = get_trails(video_id, n=n)

    print(data["video_title"])
    trails = data["trails"]
    video_id = data["video_id"]

    data_file = "data/{}_autoplay_data_{}.json".format(video_id, datetime.now().isoformat()[:19].replace(":","_"))
    result_file = "data/{}_autoplay_results_{}.csv".format(video_id, datetime.now().isoformat()[:19].replace(":","_"))

    with open(result_file, "w") as csv_file:
        csvwriter = csv.writer(csv_file)
        csvwriter.writerow([data["video_title"]])
        csvwriter.writerow([])
        for i in range(6):
            csvwriter.writerow(["{}. degree".format(i)])
            res = Counter([ x[i][1] for x in trails ]).most_common(100)
            for channel, count in dict(res).items():
                csvwriter.writerow([channel, count])    
            csvwriter.writerow([])

    #filepath = "data/{}_autoplay_data.json".format(data["video_id"])        
    json.dump(data, open(data_file, "w"), indent=4)

if __name__ == "__main__":
    autoplay_experiment()