## A 1.2-Star Launch and One Five-Star Review

The App Store rating was 1.2 stars. The only five-star review was the one Rainy wrote himself.

That's what shipping looked like for Manga Capsule, an iOS manga reader built by a two-person studio in Beijing called Capsule Studio. Nobody else works there. Just Rainy, a backend engineer with more than ten years in internet companies, and his co-founder Kins, a product designer. After roughly two years of evenings-and-weekends work, after a full year of full-time grinding with no income, after compatibility-testing against several thousand comic files, the app went live and promptly got buried. A long, angry post about it appeared on RedNote. Rainy didn't dare promote it. Competitors, meanwhile, had vibe-coded similar apps in about a month, and their reviews looked fine.

Here's the thing about a 1.2-star rating. It's not a verdict. It's a complaint list. And Rainy treated it like one.

## Two Colleagues, One Failed Startup, and a Weekly Phone Call

In 2020, Rainy and Kins worked at the same startup. It failed. That's the short version, and it's the version that matters, because the failure split them into two different lives. Rainy went to work at a big-tech company in Xierqi, Beijing's tech district, the kind of job that looks stable from the outside. Kins took a job at a mid-size internet company and started calling Rainy almost every week.

The calls were about one idea. A manga reader that wasn't painful to use. Kins had already done the market research. He'd read the user complaints about the existing apps, the ones people actually posted, the ones that described exactly what was broken. He'd drawn the product designs. He wasn't pitching a fantasy. He was pitching a fix.

Rainy told him the truth: he wrote server-side code and knew nothing about iOS.

Kins kept calling.

So yeah, the origin story isn't a hackathon. It isn't a weekend sprint. It's a designer with a folder of complaints and a backend engineer who kept saying no and eventually stopped saying no. About two years passed from the start of the project to public launch, most of it stolen from evenings and weekends. Rainy learned SwiftUI, then UIKit, on the job. Then he learned file formats. Then streaming decompression. Then network storage. Then on-device AI. The first year taught him something he probably suspected already: a full-time job meant the product would never be finished.

## He Quit a Big-Tech Job With Nothing to Show

He resigned. No revenue. No users. And the industry was in a layoff winter, which he knew meant that going back later would be nearly impossible. He wasn't walking away from a job into a safety net. He was walking away from the only net he had.

His words: "Big tech came too late for me. By the time I got there, there wasn't even soup left."

For two months he travelled and coded from hotel rooms by night, like a digital nomad. It sounds romantic. It wasn't fast enough. So he found the Beijing City Library near his home, which had just opened, and worked there from 10am to 5pm, clocking in like an employee. Not a founder's schedule. A shift.

Honestly, that detail says more about indie development than any revenue screenshot. The library opened, and he showed up.

## A Full Year, Still No Launch

A full year of full-time work went by and the app still wasn't live. No income. Savings draining. No users and no feedback. He and Kins argued. The argument had two sides and both of them were right: ship it already, against keep fixing it. Ship it and you get complaints you can act on. Keep fixing and you delay the moment the internet tells you your baby is ugly.

He says his mindset collapsed. He meditated. He walked alone at night to think about where his life was going.

That's the part nobody puts in the launch thread. The year of nothing. Not a year of building, exactly, though it was that too. A year of no signal. No users means no data. No data means no proof you're on the right track. Just you, your co-founder, and a growing pile of savings that isn't coming back.

## Streaming Was the Whole Bet

The one bet they refused to drop was streaming reading. You point the app at a NAS or a cloud drive and pages open immediately, without downloading a whole volume first. That's the feature. If you've ever waited for a whole volume to crawl onto your phone before you could read page one, you understand why it matters. If you haven't, imagine opening a book and being told to come back in ten minutes.

Streaming sounds simple when you say it out loud. It isn't. Every format had to be parsed by hand against its specification, byte by byte. EPUB, MOBI, ZIP, RAR, PDF, CBR, CBZ, AZW3. Almost no open-source library could be reused. Which is wild, because these formats aren't exotic. They're the standard containers for the exact files these users already have sitting on their drives.

Before launch, they compatibility-tested the app against several thousand comic files. Not a demo. Not ten sample files that happened to work. Several thousand, because a manga reader that chokes on your collection is worse than no manga reader at all.

One line they kept out of the product on purpose: Manga Capsule ships no manga. It's a reader, not a library. No sources, no catalogue, no content. That's a legal line and a product line at the same time, and it explains exactly who the app is for. People who already own their collection and want a better way to read it.

## The Complaint Ledger

After the bad launch, they spent four-plus months grinding through the complaint list. Then they shipped a big redesign. The bookshelf alone was rebuilt three times. Not tweaked. Rebuilt. Three times.

The app launched in September 2025, after roughly two years of building and beta testing. As of the end of August 2026, the China App Store showed 4.8 stars from 269 ratings, and the app had reached number 149 on the Books category chart. On 16 September 2026, the same listing showed 4.8 stars from 281 ratings, ranked number 171 in Books, with version 1.43 shipped on 28 August 2026. They have shipped 43 versions so far.

Forty-three versions. From 1.2 stars to 4.8.

Look at the rating count and the chart position together, though. 281 ratings is not a mass-market number. Number 171 in Books is not a household name. This isn't a rocket. It's a slow climb by a product that found a specific audience and kept earning it back one complaint at a time. The redesign wasn't the fix. The four months after it were the fix.

## Buyout Pricing for People Who Want to Own It

Revenue is real but undisclosed. Rainy's exact position: the product brings in steady income, it "barely covers one person's living costs," and Kins still has a day job. That's the honest version of indie success. Not quit-your-job money. Cover-one-person money, with the other founder still clocking in somewhere else.

Pricing is public on the App Store. In China the lifetime unlock sells for 48 yuan at the early-bird price and 68 yuan at the standard price, with a monthly plan at 6 yuan and a yearly plan at 68 yuan, plus promotional buyouts at 38 and 42 yuan. In the United States the lifetime unlock is $9.99, with a second lifetime tier at $6.99, a monthly plan at $0.99 and a yearly plan at $7.99.

Put those numbers next to each other. A yearly plan costs 68 yuan, exactly the price of the standard lifetime unlock. Twelve months of access, or the thing itself, for the same money. Which means the pricing is quietly telling you what they think: if you're going to pay, just own it. The model is buyout first, subscription second, no advertising. His reasoning: these users care about owning the thing.

That's a deliberate choice, and it's a narrow one. No ads means no free tier funded by attention. Buyout first means no recurring revenue engine. But these are people with local drives, NAS boxes and cloud storage. They already own their files. Selling them a subscription to read files they own would be weird. Rainy priced for the customer he actually had.

## The Playbook: Five Steps From 1.2 to 4.8

1. Build the tool you personally use every day.
2. Pick one hard technical capability as the moat, even if it takes two years.
3. Test it against thousands of real files before anyone else sees it.
4. Ship the ugly version so the complaint list can start.
5. Read the complaints for months, then price for ownership, not for scale.

That's the whole thing, and none of it is clever. Step one is why the product exists. Step two is streaming, the feature competitors didn't want to build. Step three is those several thousand comic files. Step four is the 1.2-star launch, which was a failure and also the only way to get the ledger. Step five is 48 yuan and $9.99 and no ads, because the people who pay want to own the thing.

The growth side is less of a playbook and more of a grind. The main channels are App Store search and RedNote, then the official website, a blog, SEO and word of mouth. He was featured in Ruan Yifeng's widely read tech weekly, which is the closest thing Chinese developers have to a mainstream mention. Paying for promotion inside RedNote was a waste of money. The single biggest traffic day came from a software-recommendation blogger, but it was a one-off. What keeps working is content aimed at very specific needs, like "reading manga on an iPad" or "a manga reader for NAS". His read on why that works: users only want to solve the problem in front of them, and almost nobody shows up to hear how great your product is.

Users are still mostly Chinese-speaking, with new ones in the United States, Japan, Hong Kong, Taiwan and Southeast Asia. His next target is English-speaking users: Reddit, X, YouTube and English SEO.

On AI, he's specific. He uses it, but he doesn't hand the project over to it. His loop is three or four rounds of architecture discussion, then a skeleton of file names, variable names and method names, then filling in the code, then reading all of it himself. His words: "AI makes writing code so easy that it hands you thousands of lines at once. But a product doesn't grow that way. It grows from something small and solid, and then you add detail, little by little."

He says most indie developers he talks to have stopped reading their own code.

And he's blunt about the internet's favourite story, the one where somebody builds an app in three days and gets rich in a month. His words: "Life is your own. You can't stake your decisions on the fantasy that you'll be the lucky one." He also says most of the AI-built apps he sees are interchangeable slop, and that the readers who pay want quality, not novelty.

## Twelve Months Later

He gives his own product 7 out of 10. Two people, no plans to hire. He says a small team is slower, but they keep the standard in their own hands.

So the scoreboard reads like this: 43 versions, 281 ratings, 4.8 stars, number 171 in Books, one person's living costs covered, one co-founder still employed elsewhere, and a product that's a 7 in its own maker's eyes. Twelve months after that 1.2-star launch, the angry RedNote post is somewhere in the past, and the complaint list has been worked through, and the bookshelf has been rebuilt three times, and the only five-star review he ever wrote himself is now one of 281.

What does he do with version 1.44?
