- [How to setup](#how-to-setup)
  - [Setup database and tools](#setup-database-and-tools)
  - [Add new market](#add-new-market)
  
# How to setup

## Setup database and tools
Clone repository:
`git clone git@github.com:hype-ecosystem/predictions_bot.git`<br />

Run setup script and make sure that there are now errors:<br />
`cd predictions_bot && sudo ./setup <path_to_store_data> <bot_api_key>`<br />

Where:<br />
<path_to_store_data> Path to the directory for script data (new markets data, robots, logs, etc)<br />
<bot_api_key>        Token for telegram bot API<br />

## Add new market
Find market symbol, ex tBTCUSD, tETHUSD, etc, from https://api.bitfinex.com/v1/symbols<br />
Run **genotick_learn** script to train genotick on new market and add it to the database.
After training is done, if no errors, market will be added to database and bot will start to make predictions on the next hour.

`cd predictions_bot && genotick_learn <start_date> <end_date> <market_symbol> <path_to_store_data>`

Where:<br />
<start_date>     Start date of the history interval in (YYYY-MM-DD) format.<br />
<end_date>       End date of the history interval in (YYYY-MM-DD) format.<br />
<market_symbol> One of the symbols from https://api.bitfinex.com/v1/symbols, upper case with prefixed with 't', f.e. tBTCUSD<br />
<path_to_store_data> Path to the directory for script data **same path as for setup script**
