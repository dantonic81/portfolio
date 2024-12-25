# Portfolio Web Application

## Introduction

The idea for this application arose from the need to track all the cryptocurrencies 
an individual may possess, usually spread across different hardware and software wallets and exchanges
and organize them in a single portfolio accessible from anywhere at any time.

The main requirement is not to spend any money on development, which means severely limited options in terms of deployment and tech stack
which in turn forces me to be as creative as possible and do much with very little.

## Evolution of an idea

- I want to see what all my cryptocurrencies are worth right now. In order to do this I first need to make a list of 
every cryptocurrency I have together with their amounts and query those against a free API e.g. CoinGecko (no API key hence process simplified) to arrive at
my current portfolio value. I also want to see information about how much each of my cryptocurrencies contributes to my overall portfolio in terms of value percentage.


- I also want this application to show me which cryptocurrencies (from the current top 100) **I don't own yet**. That should give me
visibility into which potentially good performers I'm missing. In order for this to make sense, I would have to implement alerts when a newcomer hits this list and also to sort this list by how long something has been on it. The assumption here is that
if something has been on this list for long, I'm not very interested in buying it so it can go further in the backlog.
  

- Other than these two insights, I also want to be aware of outliers as soon as they start exhibiting a certain behavior.
These in my mind are cryptocurrencies that are gaining in value so much in a short amount of time when compared to all others, that they clearly
stand out as a great investment opportunity. This is the most complex part of my application and it will utilize Machine Learning, more specifically Isolation Forest model trained on the current top 100 cryptocurrencies. 


- Once I have this logic developed, I need to deploy this application somewhere so it's accessible to me regardless of where I am at that moment and whether I'm using a laptop or my mobile phone. 


- I'm starting with a simple csv file that will hold all my crypto and will be compared against the CoinGecko API to get insights.
Render doesn't offer multiple services as part of its free tier, so I can forget about using Docker Compose with multiple services. I'll make this a single service application and deploy it via Dockerfile.
For now regular HTML and CSS is good enough together with some Bootstrap because we're serving only static pages. Python and requests library will work to get what I need from the API.


- [Render](https://render.com/) looks like a platform that could serve my needs, its free tier is good enough for me to deploy a small Dockerized Python-based webapp.


- Django feels like an overkill for this and I want to be as flexible as possible and hit the ground running in terms of quick prototyping, so I'll use Flask.


- Now that I have these three static pages serving my main insights into what I own and don't own yet (outliers will have to wait, not in the mood to eat the frog just yet),
let's build a dashboard that will serve as a landing page and will provide an immediate insight into the total portfolio value and percentage change from the day before.
Also, I would love to be able to add new assets via UI instead of editing my csv file. This means csv won't cut it, I'll need a database. I'll go with SQLite (PostgreSQL is offered as a managed instance but only a 30-day trial as part of a free tier).
This also means I need Javascript, Ajax, JQuery and some other goodies because something will have to listen to events when buttons are clicked in the UI and something will also need to send these requests produced by events
to the backend where database will be queries and something will have to carry back responses from API endpoints so that they can be represented by the frontend.


- I can add new assets through the UI, now I'd like to edit existing ones, every now and then I buy more of the crypto I already own and I earn some by staking, so I'd like to change the owned amount through the UI as well.


- Testing different functionality means ending up with test assets in the database which is something I want to have a way of maintaining. I need a delete asset functionality, but I want it to be a part of the edit asset flow instead of making it a separate functionality.


- I can now add new crypto, edit the amount of any crypto I own or delete a particular crypto altogether.
Now I want to get that percentage change to show something meaningful like how much did my portfolio lose or gain over the course of one day.

    The thought process goes like this:
  - every time this index.html is refreshed, the value of the current portfolio is written to the database together with the date, if today's date is the same as the last entry date, the portfolio value is overwritten and the date stays the same which is an update operation, if the date in the database is older than the current date, we're inserting a completely new record

  - every time this index.html is refreshed, the value of the current portfolio is compared to the portfolio value in the database for yesterday's date, if there is no value for yesterday, percentage change is not calculated and it's left as it is, if there is value for yesterday, then the current portfolio value is compared against yesterday's and a percentage change is shown in the dashboard


- I've pretty much done what I wanted on the dashboard for now, later I'll add the best performers and the worst performers ticker or something, but now I'd like to add delete functionality for every asset on the owned page, I want to be able to do that by clicking on any asset card and then go through a confirmation dialog
Also there's nothing there to indicate that cards are editable when I hover above them, a color transition like we did for items in edit asset functionality could fit well here.


- It doesn't make any sense to have portfolio allocation entries below the cards themselves, information from the allocation could be integrated into their respective cards as just another new field


- Now I'd like to explore what course outlier detection and representation will take


- I'd like to make this navbar conform to modern standards and fix some issues with how the template is selected when it's not currently viewed etc.


- I want to log every transaction I ever made, this will be a new table with id, crypto name, abbreviation, date of purchase, crypto amount, price paid in EUR, transaction_id and rate in EUR, this will be used primarily in a calculation to show earnings or losses adjusted for inflation.


- App in free tier spins down after 15 mins of inactivity, to keep it alive I've registered with this [free service](https://dashdashhard.com/), thanks Matt!


- I want to show logo for every cryptocurrency I own in its own card in owned page


- I shouldn't be able to add a new asset if it already exists in the database


- We should add top three gainers and losers to dashboard


- Develop set alerts functionality


- develop market template


- users should be able to edit existing active alerts or delete them


- develop user authentication flow (captcha)


- add auditing for login and registration


- associate data with users, handle user isolation (multi-tenant architecture)


- we should have a token that expires for users confirming email during registration


- provide users with a way to upload their own transactions file

## TODO:

- tests
- coverage
- ORM?
- withdrawal fee calculation and transactions
- logos for all tokens
- I need a notification center accessible as an icon on every page, user preference control (opt-in/opt-out)
- polling for alerts? definitely push notifications through web push as well as email notifications (sendgrid?), in-app notifications (websockets, long polling), this will have to be a scheduled job behind all of this (flask-apscheduler?)
- circulating supply vs total max supply
- tokenomics
- fully diluted valuation (current price * max supply)
- inflation rate
- staking and rewards
- market depth and liquidity
- price volatility
- database replication
- right now we're just creating and deleting users, we need functionality to edit them and change roles as well



## FIX

- outliers should be cached so we escape error 429 too many requests
- get_current_price in alerts logic should be cached
