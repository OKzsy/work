# =============================================================================
#  USGS/EROS Inventory Service Example
#  Python - JSON API
# 
#  Script Last Modified: 6/17/2020
#  Note: This example does not include any error handling!
#        Any request can throw an error, which can be found in the errorCode proprty of
#        the response (errorCode, errorMessage, and data properies are included in all responses).
#        These types of checks could be done by writing a wrapper similiar to the sendRequest function below
#  Usage: python download_data.py -u username -p password
# =============================================================================

import json
import requests
import sys
import re
import time
import argparse
import threading

path = 'F:\\test\\download'
maxthreads = 5  # Threads count for downloads
sema = threading.Semaphore(value=maxthreads)
threads = []



# send http request
def sendRequest(url, data, apiKey=None):
    json_data = json.dumps(data)

    if apiKey == None:
        response = requests.post(url, json_data)
    else:
        headers = {'X-Auth-Token': apiKey}
        response = requests.post(url, json_data, headers=headers)

    try:
        httpStatusCode = response.status_code
        if response == None:
            print("No output from service")
            sys.exit()
        output = json.loads(response.text)
        if output['errorCode'] != None:
            print(output['errorCode'], "- ", output['errorMessage'])
            sys.exit()
        if httpStatusCode == 404:
            print("404 Not Found")
            sys.exit()
        elif httpStatusCode == 401:
            print("401 Unauthorized")
            sys.exit()
        elif httpStatusCode == 400:
            print("Error Code", httpStatusCode)
            sys.exit()
    except Exception as e:
        response.close()
        print(e)
        sys.exit()
    response.close()

    return output['data']


def downloadFile(url):
    sema.acquire()
    try:
        response = requests.get(url, stream=True)
        disposition = response.headers['content-disposition']
        filename = re.findall("filename=(.+)", disposition)[0].strip("\"")
        print(f"Downloading {filename} ...\n")
        if path != "" and path[-1] != "/":
            filename = "/" + filename
        open(path + filename, 'wb').write(response.content)
        print(f"Downloaded {filename}\n")
        sema.release()
    except Exception as e:
        print(f"Failed to download from {url}. Will try to re-download.")
        sema.release()
        runDownload(threads, url)


def runDownload(threads, url):
    thread = threading.Thread(target=downloadFile, args=(url,))
    threads.append(thread)
    thread.start()


if __name__ == '__main__':
    # NOTE :: Passing credentials over a command line arguement is not considered secure
    #        and is used only for the purpose of being example - credential parameters
    #        should be gathered in a more secure way for production usage
    # Define the command line arguements

    # user input    
    # parser = argparse.ArgumentParser()
    # parser.add_argument('-u', '--username', required=True, help='Username')
    # parser.add_argument('-p', '--password', required=True, help='Password')
    #
    # args = parser.parse_args()

    # username = args.username
    # password = args.password
    username = 'hpu_zss'
    password = 'USGS120503xz'

    print("\nRunning Scripts...\n")

    serviceUrl = "https://m2m.cr.usgs.gov/api/api/json/stable/"

    # login
    payload = {'username': username, 'password': password}

    apiKey = sendRequest(serviceUrl + "login", payload)

    print("API Key: " + apiKey + "\n")

    datasetName = "sentinel_2a"

    spatialFilter = {'filterType': "mbr",
                     'lowerLeft': {'latitude': 32, 'longitude': 113},
                     'upperRight': {'latitude': 33, 'longitude': 114}}

    temporalFilter = {'start': '2021-12-13', 'end': '2021-12-14'}

    payload = {'datasetName': datasetName,
               'catalog': 'EE'}

    print("Searching datasets...\n")
    datasets = sendRequest(serviceUrl + "dataset-search", payload, apiKey)

    print("Found ", len(datasets), " datasets\n")

    # download datasets
    for dataset in datasets:

        # Because I've ran this before I know that I want GLS_ALL, I don't want to download anything I don't
        # want so we will skip any other datasets that might be found, logging it incase I want to look into
        # downloading that data in the future.
        if dataset['datasetAlias'] != datasetName:
            print("Found dataset " + dataset['collectionName'] + " but skipping it.\n")
            continue

        # I don't want to limit my results, but using the dataset-filters request, you can
        # find additional filters

        acquisitionFilter = {"end": "2021-12-14",
                             "start": "2021-12-12"}

        payload = {'datasetName': dataset['datasetAlias'],
                   'maxResults': 10,
                   'startingNumber': 1,
                   'sceneFilter': {
                       'spatialFilter': spatialFilter,
                       'acquisitionFilter': acquisitionFilter}}

        # Now I need to run a scene search to find data to download
        print("Searching scenes...\n\n")

        scenes = sendRequest(serviceUrl + "scene-search", payload, apiKey)

        # Did we find anything?
        if scenes['recordsReturned'] > 0:
            # Aggregate a list of scene ids
            sceneIds = []
            for result in scenes['results']:
                # Add this scene to the list I would like to download
                sceneIds.append(result['entityId'])

            # Find the download options for these scenes
            # NOTE :: Remember the scene list cannot exceed 50,000 items!
            payload = {'datasetName': dataset['datasetAlias'], 'entityIds': sceneIds, 'listId': 'test_Id'}

            downloadOptions = sendRequest(serviceUrl + "download-options", payload, apiKey)

            # Aggregate a list of available products
            downloads = []
            for product in downloadOptions:
                # Make sure the product is available for this scene
                if product['available'] is True and product['downloadSystem'] != 'wms':
                    downloads.append({'entityId': product['entityId'],
                                      'productId': product['id']})

            # Did we find products?
            if downloads:
                requestedDownloadsCount = len(downloads)
                # set a label for the download request
                label = "download-sample"
                payload = {'downloads': downloads,
                           'label': label}
                # Call the download to get the direct download urls
                requestResults = sendRequest(serviceUrl + "download-request", payload, apiKey)

                # PreparingDownloads has a valid link that can be used but data may not be immediately available
                # Call the download-retrieve method to get download that is available for immediate download
                if requestResults['preparingDownloads'] is not None and len(requestResults['preparingDownloads']) > 0:
                    payload = {'label': label}
                    moreDownloadUrls = sendRequest(serviceUrl + "download-retrieve", payload, apiKey)

                    downloadIds = []

                    for download in moreDownloadUrls['available']:
                        downloadIds.append(download['downloadId'])
                        print("DOWNLOAD: " + download['url'])
                        runDownload(threads, download['url'])

                    for download in moreDownloadUrls['requested']:
                        downloadIds.append(download['downloadId'])
                        print("DOWNLOAD: " + download['url'])
                        runDownload(threads, download['url'])

                    # Didn't get all of the reuested downloads, call the download-retrieve method again probably
                    # after 30 seconds
                    while len(downloadIds) < requestedDownloadsCount:
                        preparingDownloads = requestedDownloadsCount - len(downloadIds)
                        print("\n", preparingDownloads, "downloads are not available. Waiting for 30 seconds.\n")
                        time.sleep(30)
                        print("Trying to retrieve data\n")
                        moreDownloadUrls = sendRequest(serviceUrl + "download-retrieve", payload, apiKey)
                        for download in moreDownloadUrls['available']:
                            if download['downloadId'] not in downloadIds:
                                downloadIds.append(download['downloadId'])
                                print("DOWNLOAD: " + download['url'])
                                runDownload(threads, download['url'])

                else:
                    # Get all available downloads
                    for download in requestResults['availableDownloads']:
                        # TODO :: Implement a downloading routine
                        print("DOWNLOAD: " + download['url'])
                        runDownload(threads, download['url'])
                print("\nAll downloads are available to download.\n")
        else:
            print("Search found no results.\n")

    # Logout so the API Key cannot be used anymore
    endpoint = "logout"
    if sendRequest(serviceUrl + endpoint, None, apiKey) is None:
        print("Logged Out\n\n")
    else:
        print("Logout Failed\n\n")
