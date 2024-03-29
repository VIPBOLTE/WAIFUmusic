from Wifemusic.core.bot import Anony
from Wifemusic.core.dir import dirr
from Wifemusic.core.git import git
from Wifemusic.core.userbot import Userbot
from Wifemusic.misc import dbb, heroku

from .logging import LOGGER

dirr()
git()
dbb()
heroku()

app = Anony()
userbot = Userbot()


from .platforms import *

Apple = AppleAPI()
Carbon = CarbonAPI()
SoundCloud = SoundAPI()
Spotify = SpotifyAPI()
Resso = RessoAPI()
Telegram = TeleAPI()
YouTube = YouTubeAPI()
