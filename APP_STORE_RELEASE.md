# Noob Trade iOS Release Path

This project can now be wrapped as a real iOS app with Capacitor.

## What is already prepared

- Vue mobile web app tuned for portrait layout
- Capacitor configuration in [capacitor.config.ts](/Users/samuel/Documents/stock_pattern_project/capacitor.config.ts)
- Root mobile scripts in [package.json](/Users/samuel/Documents/stock_pattern_project/package.json)
- iOS preparation helper in [build_ios_release.sh](/Users/samuel/Documents/stock_pattern_project/scripts/mobile/build_ios_release.sh)
- App icon source in [noobtrade_icon.png](/Users/samuel/Documents/stock_pattern_project/launcher/assets/noobtrade_icon.png)

## One-time local setup

1. Install project mobile dependencies

```bash
cd /Users/samuel/Documents/stock_pattern_project
npm install
```

2. Install CocoaPods if it is missing

```bash
sudo gem install cocoapods
```

3. Prepare the iOS shell

```bash
cd /Users/samuel/Documents/stock_pattern_project
npm run mobile:prepare:ios
```

4. Open Xcode

```bash
cd /Users/samuel/Documents/stock_pattern_project
npm run mobile:open:ios
```

## What to do in Xcode

1. Set your Apple Team in Signing & Capabilities
2. Set bundle identifier to the production one you want to keep
3. Set App Icon using the Noob Trade orange mark
4. Update Display Name if needed
5. Test on an iPhone simulator and a real device
6. Archive the app
7. Upload to App Store Connect

## App Store Connect checklist

- App name: Noob Trade
- Subtitle: Beginner-first stock analysis workspace
- Category: Finance
- Privacy policy URL
- Support URL
- Screenshots for:
  - 6.7-inch iPhone
  - 6.5-inch iPhone
- App description
- Keywords
- Age rating questionnaire

## Current limitations before real submission

- Apple Developer account is still required
- Signing certificates and provisioning profiles must be added in Xcode
- You need a privacy policy URL before submission
- If the app uses live market APIs in production, you should document network usage in the review notes

## Recommended production flow

1. `npm run mobile:build:web`
2. `npm run mobile:sync:ios`
3. Open Xcode
4. Test on device
5. Archive
6. Submit in App Store Connect
