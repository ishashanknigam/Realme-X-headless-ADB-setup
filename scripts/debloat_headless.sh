#!/bin/bash

# Safe packages to disable for headless optimization
packages=(
    # HeyTap / NearMe (Oppo Cloud, App Market, Themes, telemetry)
    "com.heytap.pictorial"
    "com.heytap.cloud"
    "com.heytap.habit.analysis"
    "com.heytap.market"
    "com.heytap.usercenter"
    "com.heytap.datamigration"
    "com.heytap.colorfulengine"
    "com.heytap.themestore"
    "com.nearme.gamecenter"
    "com.nearme.atlas"

    # Facebook Bloat (100% safe to remove)
    "com.facebook.services"
    "com.facebook.system"
    "com.facebook.appmanager"

    # Google Bloat (Media apps not needed for server)
    "com.google.android.apps.tachyon"
    "com.google.android.videos"
    "com.google.android.apps.youtube.music"

    # ColorOS User Apps (Isolated standalone apps, 100% safe)
    "com.coloros.weather.service"
    "com.coloros.widget.smallweather"
    "com.coloros.calculator"
    "com.coloros.soundrecorder"
    "com.coloros.gallery3d"
    "com.oppo.camera"
    "com.coloros.translate.engine"
)

echo "Starting debloat process for headless device..."

for pkg in "${packages[@]}"; do
    echo "Disabling $pkg..."
    adb -s 8546e62c shell "pm disable-user --user 0 $pkg"
done

echo "Debloat complete!"
