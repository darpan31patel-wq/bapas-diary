What is live on bapas-diary.com (Cloudflare Pages project bapas-diary). Website only: nothing here touches the
daily 2pm picture. A page goes in here only after Darpan's typed yes.

- search/   Photo search ("YES GO LIVE ON PHOTO SEARCH", 23 Oct 2026). Not kept here: the deploy workflow builds it
            from the database with tools/build_search.py and site/search.html.
- travels/  Bapa's travels globe ("PERFECT GO LIVE", 23 Oct 2026). Built in its own thread; source
            /mnt/project-files/travels-globe/travels-live.html, with the tab for On this day taken out until it is live.
- calendar/ Scrolling years calendar ("perfect go live", 24 Oct 2026). Not kept here: built in the deploy with
            tools/web_calendar.py from the pinned CAL_COMMIT on branch claude/project-thread-69b2ir.
- about/    About page (text from the email thread, Darpan typed "yes, go live" 23 Oct 2026), word for word.
- through-the-years/  Bapa through the years (face page; "okay go live once github is ready", 23 Oct 2026). Not kept
            here: the deploy unpacks faces-site.tgz from release faces-mockup (built by its own thread).
- /         Home page, On this day (Darpan: yes go live, 24 Oct 2026). Not kept here: the deploy builds it with
            tools/web_day.py from the pinned DAY_COMMIT on branch claude/project-thread-2nuqbl.

Redeploy to pick up a new build from another thread: push any change here (e.g. this log). 24 Oct 00:00 UTC: faces-site.tgz with the About tab.
24 Oct 10:31 UTC: new Through the years (close up framing, big day slider), Darpan typed go live.
24 Oct 11:48 UTC: one-screen Through the years (fits the window, controls pinned at the bottom, commit 6a1069d), Darpan typed perfect go live.
24 Oct 11:51 UTC: Today page b70e8d6 (edge to edge cords, crooked hang, pendulum swing, Calendar second), Darpan typed yes perfect.
24 Oct 11:56 UTC: Calendar 5b85edc (place bubble row in the header, zoom), Darpan typed perfect.
24 Oct 13:38 UTC: new About page (both gurus, Jay Swaminarayan on top, Vachanamrut Gadhada I-3 block, centred), Darpan typed yes go live.
