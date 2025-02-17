# TODO

## Simple Upload Providers

✅ Implemented providers:
- termbin.com (text uploads)
- 0x0.st (general file uploads)
- uguu.se (temporary file uploads)
- bashupload.com (general file uploads)

## Next Steps

1. Add tests for simple providers:
   - Unit tests for each provider
   - Integration tests
   - Error handling tests
   - File size limit tests

2. Add safety features:
   - Rate limiting for each provider
   - File size validation
   - File type validation
   - Retry logic for failed uploads

3. Documentation:
   - Update main README with new providers
   - Add provider-specific documentation
   - Add examples for each provider
   - Document provider limitations

4. Provider Improvements:
   - Add provider fallback mechanism
   - Add provider selection based on file type/size
   - Add provider health checks
   - Add provider statistics

5. Code Cleanup:
   - Remove old `uploaders` directory
   - Standardize error handling across providers
   - Add type hints for all functions
   - Add docstrings for all classes/methods

## bashupload.com

I do:

>>> curl -F "file=@greeting.mp3" https://bashupload.com/

```RETURNED

=========================

Uploaded 1 file, 16 320 bytes

wget https://bashupload.com/5H6x9/greeting.mp3

=========================

```

We need to parse out the URL and transform it into

https://bashupload.com/5H6x9/greeting.mp3?download=1

Alternative syntax curl https://bashupload.com/file.txt --data-binary @/var/file.txt

## 0x0.st

https://0x0.st/

SMALL TOOL
```https://gist.github.com/gingerbeardman/5398a5feee9fa1e157b827d245678ae3
#!/bin/sh

URL="https://0x0.st"

if [ $# -eq 0 ]; then
    echo "Usage: 0x0.st FILE\n"
    exit 1
fi

FILE=$1

if [ ! -f "$FILE" ]; then
    echo "File ${FILE} not found"
    exit 1
fi

RESPONSE=$(curl -# -F "file=@${FILE}" "${URL}")

echo "${RESPONSE}" | pbcopy # to clipboard
echo "${RESPONSE}"  # to terminal
```

## uguu.se

https://uguu.se/api

Endpoint
You may POST an array of files to https://uguu.se/upload, by default you will get a json response.
If you want a response in something else than json you add a flag to specify what format you want, for example https://uguu.se/upload?output=csv.
Valid response types are: json, csv, text, html and gyazo.
Curl Example
curl -i -F files[]=@yourfile.jpeg https://uguu.se/upload

>>> curl -i -F files[]=@greeting.mp3 https://uguu.se/upload

```RETURNED
HTTP/2 200 
server: nginx
date: Mon, 17 Feb 2025 19:45:54 GMT
content-type: application/json; charset=UTF-8
strict-transport-security: max-age=31536000; includeSubDomains; preload
strict-transport-security: max-age=31536000; includeSubDomains; preload

{
    "success": true,
    "files": [
        {
            "hash": "5731e769e610edba",
            "filename": "RYqbskQu.mp3",
            "url": "https:\/\/d.uguu.se\/RYqbskQu.mp3",
            "size": 16320,
            "dupe": false
        }
    ]
}
```

## termbin.com

https://termbin.com/

Send some text and read it back:
$ echo just testing! | nc termbin.com 9999https://termbin.com/test$ curl https://termbin.com/testjust testing!
Send file contents:
$ cat ~/some_file.txt | nc termbin.com 9999
Send list of files in the current directory:
$ ls -la | nc termbin.com 9999
requirements
There is only one requirement to use this service: netcat. To check if you already have it installed, type in terminal nc or ncat or netcat.
Netcat is available on most platforms, including Windows, macOS and Linux.
alias
To simplify usage, you can add an alias to your .bashrc on Linux or .bash_profile on macOS.

linux:
echo 'alias tb="nc termbin.com 9999"' >> .bashrc

mac:
echo 'alias tb="nc termbin.com 9999"' >> .bash_profile

