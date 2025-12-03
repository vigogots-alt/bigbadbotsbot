PS C:\Users\n3m3616\Desktop\MYPrOJ
2025-12-03 08:47:16,973 | INFO | __main__ | Bot started with model gemini-2.5-flash-lite
2025-12-03 08:47:16,976 | INFO | __main__ | All subsystems initialized (learning, memory, goals, proactive, analytics)
2025-12-03 08:47:17,440 | INFO | httpx | HTTP Request: POST https://api.telegram.org/bot8522442652:AAHK0_rMNWQoAls2Yc5IRSq4x8XWbeRjqJI/getMe "HTTP/1.1 200 OK"
2025-12-03 08:47:17,446 | INFO | __main__ | Starting proactive agents for active users...
2025-12-03 08:47:17,449 | ERROR | __main__ | Failed to start proactive agent for user 7231332868: name 'logger' is not defined
2025-12-03 08:47:17,449 | INFO | __main__ | Proactive agents initialization complete
2025-12-03 08:47:17,541 | INFO | httpx | HTTP Request: POST https://api.telegram.org/bot8522442652:AAHK0_rMNWQoAls2Yc5IRSq4x8XWbeRjqJI/deleteWebhook "HTTP/1.1 200 OK"        
2025-12-03 08:47:17,544 | INFO | apscheduler.scheduler | Scheduler started
2025-12-03 08:47:17,544 | INFO | telegram.ext.Application 
| Application started
2025-12-03 08:47:37,902 | INFO | httpx | HTTP Request: POST https://api.telegram.org/bot8522442652:AAHK0_rMNWQoAls2Yc5IRSq4x8XWbeRjqJI/getUpdates "HTTP/1.1 200 OK"
2025-12-03 08:47:59,084 | INFO | httpx | HTTP Request: POST https://api.telegram.org/bot8522442652:AAHK0_rMNWQoAls2Yc5IRSq4x8XWbeRjqJI/getUpdates "HTTP/1.1 200 OK"
2025-12-03 08:48:15,091 | INFO | httpx | HTTP Request: POST https://api.telegram.org/bot8522442652:AAHK0_rMNWQoAls2Yc5IRSq4x8XWbeRjqJI/getUpdates "HTTP/1.1 200 OK"
2025-12-03 08:48:15,095 | ERROR | __main__ | Unhandled exception: name 'add_observation' is not defined
Traceback (most recent call last):
  File "C:\Users\n3m3616\AppData\Local\Programs\Python\Python313\Lib\site-packages\telegram\ext\_application.py", line 1264, in process_update
    await coroutine
  File "C:\Users\n3m3616\AppData\Local\Programs\Python\Python313\Lib\site-packages\telegram\ext\_handlers\basehandler.py", line 157, in handle_update
    return await self.callback(update, context)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\n3m3616\Desktop\MYPrOJECTS2\Sayt\bigbbadbotsbot\handlers.py", line 710, in handle_text
    await process_message(update, context, text)
  File "C:\Users\n3m3616\Desktop\MYPrOJECTS2\Sayt\bigbbadbotsbot\handlers.py", line 891, in process_message
    add_observation(user_id, text)
    ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^
  File "C:\Users\n3m3616\Desktop\MYPrOJECTS2\Sayt\bigbbadbotsbot\state.py", line 334, in add_observation
    enhanced_add_observation(user_id, message_text)       
    ~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^       
  File "C:\Users\n3m3616\Desktop\MYPrOJECTS2\Sayt\bigbbadbotsbot\advanced_memory.py", line 209, in enhanced_add_observation
    add_observation(user_id, message_text)
    ^^^^^^^^^^^^^^^
NameError: name 'add_observation' is not defined
2025-12-03 08:48:16,760 | INFO | httpx | HTTP Request: POST https://api.telegram.org/bot8522442652:AAHK0_rMNWQoAls2Yc5IRSq4x8XWbeRjqJI/sendMessage "HTTP/1.1 200 OK"