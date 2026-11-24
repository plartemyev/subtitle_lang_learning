# Offline translation bake-off - Big Lebowski samples

Phrases: last 30 cues per file through the real analyzer pipeline. Latency is per-phrase wall time in milliseconds.

Engines skipped by the 3 s/phrase budget:
- hunyuan-mt-7b: median 12856 ms/phrase over the first 5 phrases exceeds the 3000 ms budget
- milmmt-12b: median 18068 ms/phrase over the first 5 phrases exceeds the 3000 ms budget
- madlad3b: median 19772 ms/phrase over the first 5 phrases exceeds the 3000 ms budget
- hymt15-7b: median 6752 ms/phrase over the first 5 phrases exceeds the 3000 ms budget
- tower-plus-9b: median 23701 ms/phrase over the first 5 phrases exceeds the 3000 ms budget
- seed-x-7b: median 6565 ms/phrase over the first 5 phrases exceeds the 3000 ms budget
- qwen3-4b: median 7532 ms/phrase over the first 5 phrases exceeds the 3000 ms budget

## eng -> de (English to German)

| source | gemmax2-2b | hunyuan-mt-7b | hymt15-18b | hymt15-7b | madlad3b | milmmt-12b | nllb600 | qwen3-4b | qwen36-35b | seed-x-7b | tower-plus-9b |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Well, you know, strikes and gutters, ups and downs. | Nun, Sie wissen schon, Streiks und | Nun ja, Sie wissen schon – Streiks, Höhen und Tiefen im Leben… | Nun, man weiß ja, dass es immer wieder Streiks und Probleme gibt – Höhen und Tiefen eben. | Nun ja, Sie wissen schon – Streiks und Höhen und Tiefen im Leben. | s, ups and downs, ups and downs, ups and downs, ups and downs, ups and downs, ups and downs, ups and downs, ups and downs, ups and downs, ups and downs, ups and downs, ups and downs, ups and downs, downsguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersguttersgutters | Na ja, du weißt schon, Höhen und Tiefen. | Nun, Sie wissen schon, Streiks und Gitter, Höhen und Tiefen. | Nun, Sie wissen schon, Aufstiege und Abstürze, Siege und Niederlagen. | Nun, wie du weißt, Strikes und Gutter-Bälle, Hochs und Tiefs. | Nun, Sie wissen, dass es Höhen und Tiefen gibt. | Nun, Sie wissen schon, Streiks und Abflüsse, Höhen und Tiefen. |
| Sure. I got you. | Klar, ich habe Sie. | Klar – ich verstehe, was Sie meinen. | Klar. Ich habe dich untergebracht. | Klar. Ich verstehe, was Sie meinen. | Sure. Ich bekam Sie. | Klar. Ich hab dich verstanden. | Natürlich, ich hab dich. | Gerne. Ich habe es verstanden. | Sicher. Ich hab dich. | Sicherwurdest du. | Klar. Ich habe dich. |
| Yeah. Thanks, Gary. | Ja, danke, Gary. | Ja, danke, Gary. | Ja. Danke, Gary. | Ja. Danke, Gary. | Danke, Gary. Danke, Gary. Danke, Gary. | Ja. Danke, Gary. | Danke, Gary. | Ja. Danke, Gary. | Ja. Danke, Gary. | Ja, danke, Garry. | Ja. Danke, Gary. |
| Well, take care, man. Gotta get back. | Also, auf Wiedersehen, Mann. | Na ja, pass auf dich auf – ich muss zurück. | Nun, pass auf dich auf, Mann. Ich muss wieder zurück. | Na ja, pass auf dich auf, Kumpel. Ich muss jetzt weiter. | 2018. 2019. 20GottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGottaGot | Also, pass auf dich auf, Mann. | Pass auf dich auf, Mann. | Nun, passe auf dich auf, Mann. Muss zurückgehen. | Na, pass auf dich auf, Mann. Ich muss zurück. | Nun, mach's gut, Mann. Ich muss zurück. | Nun, pass auf dich auf, Mann. Ich muss zurück. |
| Sure. Take it easy, Dude. Oh, yeah. | Ja, ganz ruhig, Dude. | Klar. Mach’s langsam, Kumpel. Ach ja. | Klar. Mach dir keine Sorgen, Kumpel. Oh, ja. | Klar. Mach’s langsam, Kumpel. Ach ja. | you easy, Dude. Oh, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah, yeah.OhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOhOh | Klar. Mach es dir gemütlich, Dude. | Ganz ruhig, Kumpel. | Klar. Mach dir keine Sorgen, Mann. Oh, ja. | Sicher. Mach’s locker, Alter. Oh, ja. | Sicher, Du. Oh, ja. | Klar. Nimm es locker, Dude. Oh, ja. |
| I know that you will. | Ich weiß, dass Sie es tun werden. |  | Ich weiß, dass Sie das tun werden. |  |  |  | Ich weiß, dass du das wirst. |  | Ich weiß, dass du das tun wirst. |  |  |
| Yeah. Well, the Dude abides. | Ja. |  | Ja. Nun, der Typ hält durch. |  |  |  | Ja, der Typ hält fest. |  | Ja. Nun, der Dude bleibt. |  |  |
| Walter. | Walter. |  | Walter. |  |  |  | Das ist Walter. |  | Walter. |  |  |
| The Dude abides. | Der Dude bleibt. |  | Der Dude hält durch. |  |  |  | Der Typ bleibt. |  | Der Dude bleibt. |  |  |
| I don't know about you, but I take comfort in that. | Ich weiß nicht, wie es bei Ihnen ist, |  | Ich weiß nicht, wie es bei dir ist… Aber ich finde Trost darin. |  |  |  | Ich weiß nicht, wie es dir geht, aber das tröstet mich. |  | Ich weiß nicht, wie es dir geht, aber ich finde Trost darin. |  |  |
| It's good knowing he's out there | Es ist gut zu wissen, dass er da draußen ist |  | Es ist gut zu wissen, dass er dort draußen ist. |  |  |  | Es ist gut zu wissen, dass er da draußen ist. |  | Es ist gut zu wissen, dass er da draußen ist. |  |  |
| the Dude, tekin' 'er easy for all us sinners. | the Dude, tekin' 'er easy |  | Der Typ – er macht das ganz einfach. Für uns alle, die Sündern… |  |  |  | Das ist für uns Sünder leicht. |  | Der Dude, der es sich für uns alle Sünder einfach macht. |  |  |
| Shush. I sure hope he makes the finals. | Ich hoffe, dass er es schafft, in die Endrunde zu kommen. |  | Sei still. Ich hoffe wirklich, dass er es ins Finale schafft. |  |  |  | Ich hoffe, er kommt ins Finale. |  | Psst. Ich hoffe wirklich, dass er es ins Finale schafft. |  |  |
| Well, that about does 'er. | Nun, das macht sie schon. |  | Nun, das ist wohl alles. |  |  |  | Nun, das ist es. |  | Nun, das war's im Großen und Ganzen. |  |  |
| Wraps 'er all up. | Alles zusammen. |  | Fasse alles zusammen. |  |  |  | Sie wickelt alles zusammen. |  | Wickelt alles ein. |  |  |
| Things seem to have worked out pretty good for the Dude and Walter. | Die Dinge scheinen für den Dude und Walter gut zu laufen. |  | Es scheint, dass es für den Typen und Walter ganz gut geklappt hat. |  |  |  | Die Dinge scheinen für Dude und Walter gut gelaufen zu sein. |  | Es scheint, als wären die Dinge für den Dude und Walter ziemlich gut gelaufen. |  |  |
| And it was a pretty good story, don't ya think? | Und es war eine ziemlich gute Geschichte, |  | Und es war eine ziemlich gute Geschichte, gibt’s nicht? |  |  |  | Und es war eine ziemlich gute Geschichte, nicht wahr? |  | Und es war eine ziemlich gute Geschichte, oder nicht? |  |  |
| Made me laugh to beat the band. | Das hat mich zum Lachen gebracht. |  | Das hat mich zum Lachen gebracht. |  |  |  | Ich lachte, um die Band zu schlagen. |  | Hat mich zum Lachen gebracht, wie ein wilder Hahn. |  |  |
| Parts anyway. | Teile sowieso. |  | Jedenfalls Teile. |  |  |  | Teile sowieso. |  | Teile sowieso. |  |  |
| I didn't like seeing Donny go. | Ich mochte es nicht, Donny gehen zu sehen. |  | Es hat mir nicht gefallen, zu sehen, wie Donny geht. |  |  |  | Es gefiel mir nicht, Donny wegzusehen. |  | Ich fand es nicht schön, Donny gehen zu sehen. |  |  |
| But then I happen to know that there's a little Lebowski on the way. | Aber dann weiß ich zufällig, dass |  | Aber ich weiß zufällig, dass es auf dem Weg noch einen kleinen „Lebowski“ gibt. |  |  |  | Aber dann weiß ich zufällig, dass ein kleiner Lebowski unterwegs ist. |  | Aber dann weiß ich zufällig, dass ein kleiner Lebowski unterwegs ist. |  |  |
| I guess that's the way the whole dumed human comedy... | Ich vermute, das ist der Weg |  | Ich glaube, das ist auch die Art und Weise, wie sich die ganze menschliche Komödie abspielt… |  |  |  | Ich schätze, das ist die Art, wie die ganze dumme menschliche Komödie... |  | Ich schätze, so läuft die ganze dumme menschliche Komödie... |  |  |
| keeps perpetuating itself... | verlängert sich immer weiter... |  | Es bleibt weiterhin bestehen… |  |  |  | und sich selbst weiterentwickelt... |  | setzt sich fortwährend fort... |  |  |
| down through the generations. | über die Generationen hinweg. |  | Von Generation zu Generation weitergegeben. |  |  |  | durch die Generationen. |  | durch die Generationen hindurch. |  |  |
| Westward the wagons, across the sands of time... | Westwärts die Wagen, |  | Nach Westen hin – die Wagen… über die Sandflächen der Zeit… |  |  |  | Westenwärts die Wagen, über den Sand der Zeit... |  | Nach Westen, die Wagen, durch den Sand der Zeit... |  |  |
| until we | bis wir |  | bis wir… |  |  |  | bis wir |  | bis wir |  |  |
| Oh, look at me. I'm rambling again. | Oh, guck mich an. |  | Oh, schau mich mal an. Ich rede wieder Unsinn. |  |  |  | Oh, sieh mich an, ich ramble wieder. |  | Oh, schau mich an. Ich rede wieder ins Leere. |  |  |
| Well, I hope you folks enjoyed yourselves. | Nun, ich hoffe, ihr Leute |  | Nun, ich hoffe, dass euch die Zeit mit euren Lieben gefallen hat. |  |  |  | Ich hoffe, ihr habt euch genossen. |  | Nun, ich hoffe, ihr habt euch gut amüsiert. |  |  |
| Catch you later on down the trail. | Bis bald auf dem Weg. |  | Wir sehen uns später wieder am Ende des Weges. |  |  |  | Wir sehen uns später auf dem Weg. |  | Bis später auf dem Weg! |  |  |
| Say, friend. You got any more of that good sarsaparilla? | Sag, Freund. Hast du noch mehr davon? |  | Sagen Sie mir, Freund. Haben Sie noch etwas von diesem leckeren Sarsaparilla übrig? |  |  |  | Hast du noch etwas von dieser guten Sarsaparilla? |  | Sag mal, Freund. Hast du noch mehr von diesem guten Sarsaparilla? |  |  |

Latency: gemmax2-2b: 3.8s/phrase | hunyuan-mt-7b: 17.2s/phrase | hymt15-18b: 3.7s/phrase | hymt15-7b: 9.6s/phrase | madlad3b: 72.1s/phrase | milmmt-12b: 18.1s/phrase | nllb600: 1.4s/phrase | qwen3-4b: 10.1s/phrase | qwen36-35b: 1.1s/phrase | seed-x-7b: 9.0s/phrase | tower-plus-9b: 30.3s/phrase

## eng -> ru (English to Russian)

| source | gemmax2-2b | hymt15-18b | nllb600 | qwen36-35b |
|---|---|---|---|---|
| Well, you know, strikes and gutters, ups and downs. | Ну, вы знаете, забастовки и | Ну, знаете ли… Были забастовки и все такое. Все менялось от приятного до неприятного. | Ну, знаешь, удары и канавы, взлеты и падения. | Ну, вы знаете, страйки и гуттеры, взлёты и падения. |
| Sure. I got you. | Конечно, я понял. | Конечно. Я выполню вашу просьбу. | Конечно, я тебя пойму. | Конечно. Я тебя понял. |
| Yeah. Thanks, Gary. | Да, спасибо, Гэри. | Да. Спасибо, Гэри. | Да, спасибо, Гэри. | Да. Спасибо, Гэри. |
| Well, take care, man. Gotta get back. | Ну, берегись, мужик. | Ну, берегись, чувак. Мне нужно вернуться. | Берегись, мужик. | Ну, береги себя, чувак. Мне пора возвращаться. |
| Sure. Take it easy, Dude. Oh, yeah. | Да, успокойся, чувак. | Конечно. Не волнуйся, дружище. | Конечно, успокойся, чувак. | Конечно. Расслабься, чувак. О, да. |
| I know that you will. | Я знаю, что вы сделаете это. | Я знаю, что вы так и сделаете. | Я знаю, что ты это сделаешь. | Я знаю, что ты так и сделаешь. |
| Yeah. Well, the Dude abides. | Да. | Да. Ну, этот парень все равно остается таким же. | Ну, парень выдерживает. | Да. Ну, Дядя продолжает жить. |
| Walter. | Уолтер. | Вальтер. | Уолтер. | Уолтер. |
| The Dude abides. | Дуд остается. | Дуде молчит. | Парень держится. | Дудь живёт. |
| I don't know about you, but I take comfort in that. | Я не знаю, как вы, | Не знаю, как вы, но меня это утешает. | Не знаю, как ты, но это меня утешает. | Не знаю, как у вас, но я нахожу в этом утешение. |
| It's good knowing he's out there | Хорошо, что он там | Хорошо знать, что он находится там. | Хорошо знать, что он там. | Хорошо знать, что он где-то там. |
| the Dude, tekin' 'er easy for all us sinners. | Дудь, берегись с ней | Этот парень просто легко справляется со всеми нами, грешниками. | Чувак, это легко для всех нас грешников. | Дуд, расслабляясь для всех нас, грешников. |
| Shush. I sure hope he makes the finals. | Я надеюсь, что он пройдет в финал. | Тсс… Надеюсь, он сможет выйти в финал. | Я надеюсь, что он выйдет в финал. | Тише. Надеюсь, он выйдет в финал. |
| Well, that about does 'er. | Ну, это и так. | Ну, это уже все. | Ну, вот и всё. | Ну, вот и всё. |
| Wraps 'er all up. | Все завершилось. | Все это можно объяснить одним словом. | Завязывает всё. | Всё это обёртывается. |
| Things seem to have worked out pretty good for the Dude and Walter. | Похоже, что все получилось | Похоже, что все прошло довольно хорошо для Дуда и Уолтера. | Похоже, что все получилось довольно хорошо для Дюда и Уолтера. | Похоже, у Дуда и Уолтера всё сложилось довольно неплохо. |
| And it was a pretty good story, don't ya think? | И это была довольно хорошая история, | И это была довольно интересная история, не правда ли? | И это была довольно хорошая история, не так ли? | И это была довольно интересная история, не так ли? |
| Made me laugh to beat the band. | Ты заставил меня смеяться, чтобы победить группу. | Это заставило меня засмеяться. | Заставляет меня смеяться, чтобы победить группу. | Заставило меня смеяться до упаду. |
| Parts anyway. | В любом случае, части. | В любом случае, это всего лишь части. | Части в любом случае. | Всё равно детали. |
| I didn't like seeing Donny go. | Мне не нравилось, когда Донни уезжал. | Мне не понравилось видеть, как уходит Донни. | Мне не нравилось, когда Донни уходил. | Мне не понравилось видеть, как Донни уходит. |
| But then I happen to know that there's a little Lebowski on the way. | Но потом я случайно узнал, что | Но я вдруг узнаю, что на пути к нам находится еще один „Лебовски“. | Но потом я случайно узнал, что по дороге едет маленький Лебовски. | Но потом я узнаю, что на подходе маленький Лебовски. |
| I guess that's the way the whole dumed human comedy... | Я думаю, что так и должно быть | Думаю, так и есть… Вся эта человеческая комедия происходит именно так. | Полагаю, именно так вся эта дурацкая человеческая комедия... | Думаю, так и разыгрывается вся эта дурманящая человеческая комедия... |
| keeps perpetuating itself... | продолжает само воспроизводство... | Продолжает существовать… | продолжает увековечивать себя... | продолжает бесконечно воспроизводить себя... |
| down through the generations. | на протяжении поколений. | Происходит это на протяжении многих поколений. | На протяжении поколений. | из поколения в поколение. |
| Westward the wagons, across the sands of time... | В западном направлении вагоны, | На западе движутся повозки… Через пустынные просторы времени… | На запад, по колесницам, через песок времени... | На запад, повозки, через пески времени... |
| until we | до тех пор, пока мы | пока что | До тех пор пока мы | пока мы |
| Oh, look at me. I'm rambling again. | О, посмотрите на меня. | О, посмотрите на меня. Я снова бесцельно говорю всякую ерунду. | Посмотри на меня, я опять блуждаю. | О, посмотри на меня. Я снова болтаю без умолку. |
| Well, I hope you folks enjoyed yourselves. | Ну, надеюсь, вам понравилось. | Надеюсь, вам понравилось. | Надеюсь, вам понравилось. | Ну, я надеюсь, вам всем понравилось. |
| Catch you later on down the trail. | До встречи на тропинке. | Увидимся позже по дороге. | Увидимся позже. | Увидимся позже на тропе. |
| Say, friend. You got any more of that good sarsaparilla? | Скажи, друг. У тебя еще есть этого хорошего сассапарилла? | Ну что ж, друг мой. У вас ещё есть эта вкусная сарсапаралина? | Приятель, у тебя есть еще такой хороший сарсапарилла? | Слушай, приятель. У тебя ещё есть эта хорошая сарсапарилла? |

Latency: gemmax2-2b: 3.8s/phrase | hymt15-18b: 3.8s/phrase | nllb600: 2.2s/phrase | qwen36-35b: 1.1s/phrase

## eng -> th (English to Thai)

| source | gemmax2-2b | hymt15-18b | nllb600 | qwen36-35b | typhoon-15-4b |
|---|---|---|---|---|---|
| Well, you know, strikes and gutters, ups and downs. | ก็คุณก็รู้ว่า การนัดหยุดงานและ | ก็…คุณรู้ดีนะ…มีทั้งการนัดหยุดงาน และสถานการณ์ที่ไม่แน่นอน…มีทั้งช่วงที่ดีและช่วงที่แย่เลย. | รู้มั้ย การท่าท่าท่าท่าท่าท่าท่าท่าท่าท่าท่าท่าท่าท่าท่าท่าท่าท่าท่าท่า | ก็อย่างที่คุณรู้แหละ การStrikeและGutterขึ้นๆลงๆ | ก็รู้ใช่มั้ง ชัยชนะ ล้มเหลว ขึ้นๆ ลงๆ |
| Sure. I got you. | ได้ค่ะ ฉันเข้าใจแล้ว | แน่นอนค่ะ ฉันเข้าใจความหมายของคุณแล้ว. | แน่นอน ฉันมีคุณ | แน่นอน ฉันเข้าใจแล้ว | แน่นอน ฉันจัดการให้ |
| Yeah. Thanks, Gary. | ขอบคุณนะ แกรี่ | ใช่ค่ะ ขอบคุณนะ เจอร์รี่. | ใช่ ขอบคุณแกรีย์ | ใช่ครับ ขอบคุณครับ, แกรี่ | ใช่ ขอบคุณ แกรี่ |
| Well, take care, man. Gotta get back. | เอาล่ะ ระวังตัวนะ | เอาล่ะ, ขอให้คุณดูแลตัวเองดีๆ นะ. ฉันต้องกลับไปแล้ว. | ระวังตัว นายต้องกลับ | ว่าแล้ว ก็ดูแลตัวเองด้วยนะเพื่อน ต้องกลับแล้ว | เอาล่ะ ดูแลตัวเองนะเพื่อน ต้องกลับไปแล้ว |
| Sure. Take it easy, Dude. Oh, yeah. | เอาละ, เอาเบาๆ, Dude. | แน่นอนสิ… ไม่ต้องกังวลนะ, เพื่อนเอ๋ย. | แน่ใจ ใจเย็นๆ | แน่นอนครับ ผ่อนคลายหน่อยนะเพื่อน โอ้ ใช่เลย | แน่นอน ใจเย็นๆ น้า อ้อ ใช่ |
| I know that you will. | ฉันรู้ว่าคุณจะทำ | ฉันรู้ว่าคุณจะทำเช่นนั้นแน่นอน. | ผมรู้ว่าคุณจะทํา | ฉันรู้ว่าคุณจะทำได้ | ฉันรู้ว่าเธอจะทำได้ |
| Yeah. Well, the Dude abides. | ใช่. | ใช่. เอาเป็นว่า… ผู้ชายคนนั้นก็ยังคงอยู่ที่นั่นต่อไป. | ใช่ ดีดุ๊ดยังคงอยู่ | ใช่แล้ว ดี๊ดก็อยู่อย่างนั้นแหละ | ใช่ เอาล่ะ Dude ยึดมั่น |
| Walter. | วอลเตอร์ | วอลเตอร์. | วอลเตอร์ | วอลเตอร์ | วอลเตอร์ |
| The Dude abides. | เดดอยู่ที่นี่ | เดอะดูด์ยอมรับมันไปเลย. | แดดด อยู่ | เดอะดูดยังคงอยู่ | เดอะ ดูดี้ อะบิดส์ |
| I don't know about you, but I take comfort in that. | ฉันไม่รู้ว่าคุณเป็นยังไง แต่ฉันรู้สึกสบายใจ | ฉันไม่รู้ว่าคุณเป็นอย่างไรบ้าง… แต่ฉันก็รู้สึกโล่งใจกับเรื่องนั้นนะ. | ฉันไม่รู้เกี่ยวกับคุณ แต่ฉันได้รับความสบายใจในนั้น | ไม่รู้ว่าเธอเป็นยังไง แต่ฉันรู้สึกสบายใจกับเรื่องนั้น | ฉันไม่รู้ว่าคุณเป็นอย่างไร แต่ฉันรู้สึกสบายใจกับสิ่งนั้น |
| It's good knowing he's out there | ดีที่รู้ว่าเขาอยู่ที่นั่น | ดีใจที่รู้ว่าเขาอยู่ข้างนอกนั้น | ดีที่รู้ว่าเขาอยู่ข้างนอก | ดีใจที่ได้รู้ว่าเขายังอยู่ตรงนั้น | ดีนะที่รู้ว่าเขายังอยู่ตรงนั้น |
| the Dude, tekin' 'er easy for all us sinners. | เพื่อน, ให้มันง่าย | ผู้ชายคนนั้น… ทำได้ง่ายๆ เลยนะ สำหรับพวกเราทุกคนที่เป็นคนบาปกันทั้งนั้น. | เพื่อนเทคนิคมันง่ายสําหรับเราทุกคน | เดอะดู๊ด กำลังพักผ่อนอย่างสบายๆ เพื่อพวกเราทุกคนที่เป็นคนบาป | เดอะดูด กำลังเอาเธอไปแบบไม่รีบร้อน สำหรับพวกบาปทุกคน |
| Shush. I sure hope he makes the finals. | หวังว่าเขาจะเข้ารอบสุดท้าย | ชูช… ฉันหวังเป็นอย่างยิ่งว่าเขาจะสามารถผ่านเข้าสู่รอบสุดท้ายได้. | เงียบเถอะ ฉันหวังว่าเขาจะเข้ารอบชิงชนะเลิศ | เงียบๆ ฉันหวังว่าเขาจะผ่านเข้ารอบชิงชนะเลิศนะ | ชู่ส ฉันหวังจริงๆ |
| Well, that about does 'er. | ก็ประมาณนั้นแหละ | เออ, นั่นก็พอแล้ว. | ก็พอดีนะ | เอ่อ ก็ประมาณนั้นแหละ | เอาล่ะ นั่นก็พอแล้ว |
| Wraps 'er all up. | ห่อมันทั้งหมด | จัดการทุกอย่างให้เรียบร้อยเลย. | จับมันไปหมด | ห่อทุกอย่างเข้าด้วยกัน | ห่อทุกอย่างไว้หมดเลย |
| Things seem to have worked out pretty good for the Dude and Walter. | ดูเหมือนว่าทุกอย่างจะผ่านไปได้ด้วยดีสำหรับ Dude และ Walter | ดูเหมือนว่าทุกอย่างจะผ่านไปได้ด้วยดีสำหรับดูกและวอลเตอร์. | สถานการณ์ดูเหมือนจะออกได้ดีสําหรับดุ๊ดและวอลเตอร์ | ดูเหมือนว่าทุกสิ่งจะดำเนินไปด้วยดีสำหรับเดอะดูด์และวอลเตอร์ | ดูเหมือนทุกอย่างจะออกมาดีสำหรับดูดี้กับวอลเตอร์ |
| And it was a pretty good story, don't ya think? | และมันก็เป็นเรื่องที่ดีมาก | และมันก็เป็นเรื่องราวที่น่าสนใจดีเลยนะ… คุณไม่คิดอย่างนั้นเหรอ? | และมันก็เป็นเรื่องดีมากใช่ไหม? | และมันก็เรื่องเล่าที่ค่อนข้างน่าสนใจนะ คุณคิดว่ายังไง? | และมันก็เป็นเรื่องราวที่ดีมากเลยนะ เธอว่าไหม? |
| Made me laugh to beat the band. | ทำให้ฉันหัวเราะจนลืมวงดนตรี | ทำให้ฉันต้องหัวเราะออกมาเลย. | ทําให้ฉันหัวเราะเพื่อเอาชนะวง | ทำให้ฉันหัวเราะอย่างหนักเลย | ทำให้ฉันหัวเราะจนแทบขาด |
| Parts anyway. | ส่วนใด ๆ | ส่วนประกอบต่างๆ ก็ยังคงมีอยู่เช่นกัน. | อะไหล่ยังไง | ชิ้นส่วนอยู่ดี ๆ | ส่วนอื่นๆ ก็เหมือนกัน |
| I didn't like seeing Donny go. | ฉันไม่ชอบเห็นดอนนี่ไป | ฉันไม่ชอบที่ต้องเห็นดอนนี่จากไปเลย. | ฉันไม่ชอบที่ดอนนี่ไป | ฉันไม่ชอบที่เห็นดอนนี่จากไป | ฉันไม่ชอบเห็นดอนนี่จากไป |
| But then I happen to know that there's a little Lebowski on the way. | แต่แล้วฉันก็รู้ว่า | แต่แล้วฉันก็รู้ว่า มี “เลบอว์สกี้” อยู่ในระหว่างทางนะ. | แต่หลังจากนั้นฉันก็รู้ว่า มีเลโบวสกี้น้อยอยู่บนทาง | แต่แล้วฉันก็รู้ว่ามีเด็กน้อยชื่อเลอบอฟสกีกำลังจะถือกำเนิดขึ้น | แต่แล้วฉันก็รู้บ้างว่า มีเลบอฟสกี้เล็กๆ รออยู่ข้างหน้า |
| I guess that's the way the whole dumed human comedy... | ฉันเดาว่านั่นคือวิธี | ฉันคิดว่านั่นแหละคือวิธีการของทั้งเรื่องนี้… | ฉันเดาว่านั่นคือวิธีการทั้งหมดโง่มนุษย์การแสดงโง่ ... | ฉันคิดว่านั่นคือวิธีที่... ละครมนุษย์ทั้งเรื่องดำเนินไป... | ฉันเดาว่านั่นแหละ วิธีที่ทั้งเรื่องตลกมนุษย์ที่เต็มไปด้วยความโง่เขลา... |
| keeps perpetuating itself... | ยังคงดำเนินต่อไป... | ยังคงดำรงอยู่ต่อไปเรื่อยๆ… | ยังคงต่อเนื่องตัวเอง... | ยังคงขยายตัวไปเรื่อยๆ... | ยังคงทำตัวเองต่อเนื่องไปเรื่อยๆ... |
| down through the generations. | ผ่านไปหลายรุ่น | สืบทอดมาจากรุ่นสู่รุ่น | ผ่านหลายรุ่น | สืบต่อกันมาหลายชั่วอายุคน | สืบต่อกันมาหลายรุ่น |
| Westward the wagons, across the sands of time... | รถลากตะวันตก, | ไปทางทิศตะวันตก… ข้ามผ่านทะเลทรายแห่งเวลา… | ไปทางตะวันตก รถบรรทุกข้ามทรายของเวลา | มุ่งหน้าไปทางตะวันตก ด้วยรถม้าข้ามผ่านกาลเวลา... | ขับรถม้าไปทางทิศตะวันตก ข้ามทรายแห่งกาลเวลา... |
| until we | จนกว่าเรา | จนกระทั่งเรา… | จนกว่าเรา | จนกว่าเรา | จนกว่าเราจะ |
| Oh, look at me. I'm rambling again. | โอ้, มองมาที่ฉัน | โอ้, ดูฉันสิ… ฉันกำลังพูดไร้สาระอีกแล้ว. | โอ้ ดูฉันสิ ฉันกําลังยุ่งยุ่งอีกครั้ง | โอ้ ดูฉันสิ ฉัน又开始พูดเรื่อยเปื่อยอีกแล้ว | โอ้ ดูฉันสิ ฉันพูดวกวนอีกแล้ว |
| Well, I hope you folks enjoyed yourselves. | หวังว่าพวกคุณคงสนุกกันนะ | เอาล่ะ… หวังว่าทุกคนจะมีความสุขกับการมาเยือนที่นี่นะ. | ผมหวังว่าพวกคุณสนุกไป | ดีครับ ผมหวังว่าคุณๆ จะสนุกกับกิจกรรมนะครับ | เอาล่ะ ฉันหวังว่าพวกคุณจะสนุกนะ |
| Catch you later on down the trail. | เจอกันทีหลังบนเส้นทาง | เจอกันอีกทีในตอนหลังนะ. | เจอกันในตอนหลัง | เจอกันใหม่บนเส้นทางข้างหน้า | เจอกันทีหลังทางนี้ |
| Say, friend. You got any more of that good sarsaparilla? | บอกเพื่อนเถอะ มีอีกไหม | บอกมาเถอะเพื่อน… คุณยังมีซาร์ซาปาริลล่านั้นอยู่อีกไหม? | นี่เพื่อน คุณมีซาร์ซาริลาอีกมั้ย | ว่าไงเพื่อน มีน้ำสมุนไพรซาร์ซาพาริลลาดีๆ แบบนั้นอีกไหม? | เฮ้ เพื่อน นายมีซาร์ซาพาริลลาดีๆ แบบนั้นอีกไหม? |

Latency: gemmax2-2b: 4.1s/phrase | hymt15-18b: 5.8s/phrase | nllb600: 1.5s/phrase | qwen36-35b: 1.0s/phrase | typhoon-15-4b: 8.8s/phrase

## deu -> en (German to English)

| source | gemmax2-2b | hymt15-18b | nllb600 | qwen36-35b |
|---|---|---|---|---|
| Mach's gut, Dude. | Do it well, Dude. | Come on, buddy. | Do it right, dude. | Take care, Dude. |
| Ich weiß, das wirst du... | I know you will... | I know that you will do it… | I know you will. | I know, you will... |
| Der Dude hält durch. | The Dude is holding on. | That guy is holding on. | Dude's keeping up. | The Dude holds on. |
| Der Dude hält durch... | The Dude is holding on... | That guy is holding on… | The dude keeps going... | The Dude holds on... |
| Wenn Sie mich fragen, ein großer Trost. | If you ask me, | If you ask me… it’s a great comfort. | If you ask me, a great consolation. | If you ask me, it's a great comfort. |
| Gut zu wissen, daß es ihn gibt. | It is good to know that it exists. | It’s good to know that it exists. | It's good to know there is. | Good to know that he exists. |
| Der wird's schon bringen. Auch ohne uns Sünder. | He will bring it. | He will definitely make it happen. Even without us sinners being involved. | He'll make it, even without us sinners. | He'll manage to pull it off. Even without us sinners. |
| Hoffe, er schafft's ins Finale. | I hope he makes it to the final. | I hope he’s able to make it to the final. | I hope he makes it to the finals. | Hope he makes it to the final. |
| Nun denn, | Well then, | Well then… | Well, then, | Well then, |
| das wär's dann wohl. | that would be it. | Well, that would be it then. | I guess that's it. | That would be it, then. |
| Am Ende lief doch alles ganz gut für den Dude und Walter. | In the end, everything went well | In the end, everything went well for the Dude and Walter. | In the end, everything was fine for the Dude and Walter. | In the end, everything turned out pretty well for the Dude and Walter. |
| 'Ne saubere, gute Geschichte, | 'Ne a clean, good story, | It’s a good story, indeed. | 'Not a clean, good story, | 'Not clean, good story,' |
| oder? | or? | Or what? | You're not? | Or? |
| Mußte oft brüllen vor Lachen. | I had to often scream with laughter. | I often had to laugh loudly. | Had to make a lot of noise before laughing. | I had to yell out loud from laughing so hard. |
| Meistens jedenfalls. | Most of the time, anyway. | Most of the time, anyway. | Most of the time. | Mostly, anyway. |
| Gefiel mir nicht, daß Donny gehen mußte. | I didn't like it, | I didn’t like it at all that Donny had to leave. | I didn't like Donny having to leave. | I didn't like the fact that Donny had to leave. |
| Zufällig weiß ich aber, daß ein... | I happen to know that a... | By chance, I know that a… | I happen to know that a... | By chance, I happen to know that a... |
| kleiner Lebowski unterwegs ist. | little Lebowski is on the move. | It’s just a little Lebowski on the way. | Little Lebowski is on his way. | The Little Lebowski is on the move. |
| So setzt sich also die menschliche Komödie... | So it goes on like this | So, that’s how human comedy works… | So this is the human comedy... | Thus, the human comedy unfolds... |
| fort. | forward. | Fort. | I'm on my way. | fort. |
| Durch alle Generationen, | Through all generations, | Through all generations. | Through all generations, | Through all generations, |
| westwärts, | westward, | Westward. | to the west, | westward, |
| über den Sand der Zeit bis... | over the sand of time until... | Over the sands of time… | over the sands of time until... | over the sand of time until... |
| Ach je, | Oh, yes, | Oh, really… | Oh, my God. | Oh dear, |
| ich schweife schon wieder ab. | I'm already drifting off. | I’m getting off track again. | I'm going back. | I'm drifting off topic again. |
| Macht's gut, Leute. | It's okay, guys. | It’s good to have people like that around. | All right, people. | That's Macht's gut, folks. |
| Ich sehe euch später. | I'll see you later. | I’ll see you later. | I'll see you guys later. | I'll see you later. |
| Guter Mann, | Good man, | Good man. | That's a good man. | Good man, |
| kann ich noch 'nen Sarsaparilla haben? | can I still have | Can I still get some sarsaparilla? | Can I have another Sarsaparilla? | Can I have another Sarsaparilla? |
| Untertitel: V. Maidit | Subtitle: V. Maidit | Subtitle: V. Maidit | Subtitle: V. Maidit | Subtitle: V. Maidit |

Latency: gemmax2-2b: 3.3s/phrase | hymt15-18b: 2.7s/phrase | nllb600: 1.2s/phrase | qwen36-35b: 0.8s/phrase

## deu -> ru (German to Russian)

| source | gemmax2-2b | hymt15-18b | nllb600 | qwen36-35b |
|---|---|---|---|---|
| Mach's gut, Dude. | Будь в порядке, чувак. | Ну что ж, парень. | Давай, чувак. | Делай как знаешь, чувак. |
| Ich weiß, das wirst du... | Я знаю, что ты... | Я знаю, что ты так и сделаешь… | Я знаю, что ты... | Я знаю, ты это сделаешь... |
| Der Dude hält durch. | Дуд сдержал слово. | Этот парень выдерживает. | Дуд продержится. | Дядя Дад держится. |
| Der Dude hält durch... | Дудл выдерживает... | Этот парень выдерживает… | Этот чувак держится... | Дядя Дад держится... |
| Wenn Sie mich fragen, ein großer Trost. | Если вы спросите меня, | Если вы спросите меня… Это действительно большое утешение. | Если вы спросите меня, это большое утешение. | Если вы спросите меня, это большое утешение. |
| Gut zu wissen, daß es ihn gibt. | Хорошо знать, что он существует. | Хорошо знать, что такое существует. | Хорошо знать, что он существует. | Хорошо знать, что он существует. |
| Der wird's schon bringen. Auch ohne uns Sünder. | Он все докажет. | Он обязательно справится с этой задачей. Даже без нас, грешников. | Он справится, даже без нас, грешников. | Он всё равно справится. Даже без нас, грешников. |
| Hoffe, er schafft's ins Finale. | Надеюсь, он добьется финала. | Надеюсь, он сможет пройти в финал. | Надеюсь, он выйдет в финал. | Надеюсь, он выйдет в финал. |
| Nun denn, | Ну тогда, | Ну что же… | Что ж, | Ну что ж, |
| das wär's dann wohl. | Тогда это было бы. | Вот так и будет. | Я думаю, это было бы хорошо. | Вот и всё. |
| Am Ende lief doch alles ganz gut für den Dude und Walter. | В конце концов все прошло хорошо | В конце концов все прошло очень хорошо для Дуда и Уолтера. | В конце концов все было хорошо для Дюда и Уолтера. | В конце концов, всё закончилось довольно хорошо для чувака и Уолтера. |
| 'Ne saubere, gute Geschichte, | 'Не чистая, хорошая история, | Это нечестная, подлая история. | "Не чистая, хорошая история, | «Не очень чистая, но хорошая история». |
| oder? | или? | Или что же? | Не так ли? | или? |
| Mußte oft brüllen vor Lachen. | Я часто рычала от смеха. | Часто приходилось кричать от смеха. | Должен был часто кричать перед смехом. | Мне часто приходилось кричать от смеха. |
| Meistens jedenfalls. | По крайней мере, в большинстве случаев. | В основном, да. | В большинстве случаев. | В большинстве случаев, во всяком случае. |
| Gefiel mir nicht, daß Donny gehen mußte. | Мне не понравилось, | Мне не понравилось, что Донни должна уйти. | Мне не понравилось, что Донни должен был уйти. | Мне не понравилось, что Донни пришлось уйти. |
| Zufällig weiß ich aber, daß ein... | Но, как ни странно, я знаю, что... | К счастью, я знаю, что… | Но я случайно знаю, что... | Но случайно я знаю, что... |
| kleiner Lebowski unterwegs ist. | Маленький Лебоски в пути. | Клейнер Лебовски в пути. | Маленький Лебовский в пути. | маленький Лейбович в пути. |
| So setzt sich also die menschliche Komödie... | Так что, если вы | Вот так и складывается человеческая комедия… | Так происходит человеческая комедия... | Итак, так и разворачивается человеческая комедия... |
| fort. | продолжать. | Форт. | Продолжайте. | форт. |
| Durch alle Generationen, | Через все поколения, | Через все поколения. | На протяжении всех поколений | Через все поколения, |
| westwärts, | на запад, | на запад. | на запад, | на запад, |
| über den Sand der Zeit bis... | с песком времени до... | По песку времени… | На песке времени до... | через песок времени до... |
| Ach je, | Ах да, | Ах вот… | О, никогда. | Ох, бедный, |
| ich schweife schon wieder ab. | Я снова заблуждаюсь. | Я снова отвожусь от темы. | Я опять уезжаю. | Я снова ушёл в сторону. |
| Macht's gut, Leute. | Хорошо, ребята. | Хорошо, люди. | Все хорошо, ребята. | Это просто отлично, ребята. |
| Ich sehe euch später. | Увидимся позже. | Я увижу вас позже. | Увидимся позже. | Увидимся позже. |
| Guter Mann, | Хороший человек, | Хороший человек. | Хороший человек. | Хороший человек, |
| kann ich noch 'nen Sarsaparilla haben? | могу ли я еще | Могу ли я ещё получить немного сарсапарали? | Можно мне ещё одну сарсапариллу? | Можно мне ещё сарсапарилли? |
| Untertitel: V. Maidit | Подзаголовок: V. Maidit | Подзаголовок: V. Маидит | Подзаголовок: V. Maidit | Субтитры: В. Майдит |

Latency: gemmax2-2b: 3.1s/phrase | hymt15-18b: 3.2s/phrase | nllb600: 1.2s/phrase | qwen36-35b: 0.9s/phrase

## deu -> th (German to Thai)

| source | gemmax2-2b | hymt15-18b | nllb600 | qwen36-35b |
|---|---|---|---|---|
| Mach's gut, Dude. | ทำดีๆนะเพื่อน | มันเป็นเรื่องปกตินะ, เจ้านาย. | ทํามันได้ดีนะเพื่อน | ทำได้ดีมากนะ เพื่อน |
| Ich weiß, das wirst du... | ฉันรู้ว่าคุณจะ... | ฉันรู้ว่าเธอจะทำแบบนั้น… | ผมรู้ว่าคุณจะ... | ฉันรู้ว่าคุณคงจะ... |
| Der Dude hält durch. | Dude ก็ยังอยู่ | ผู้ชายคนนั้นยังคงยืนหยัดอยู่ได้. | คนร้ายนั่นคงคงอยู่ | เดอะดูดยังคงสู้ต่อไป |
| Der Dude hält durch... | Dude จะผ่านไปได้... | ผู้ชายคนนั้นยังคงยืนหยัดอยู่… | แฟนนั่นคงอยู่... | เดอะดูดยังคงสู้ต่อไป... |
| Wenn Sie mich fragen, ein großer Trost. | ถ้าคุณถามผม | ถ้าคุณถามฉัน… นั่นก็เป็นเรื่องที่ช่วยให้ใจสบายขึ้นมากเลยค่ะ. | ถ้าคุณถามผม สบายใจมาก | ถ้าถามผม มันก็เป็นความปลอบใจอย่างใหญ่หลวง |
| Gut zu wissen, daß es ihn gibt. | ดีที่รู้ว่ามันมีอยู่ | ดีที่ได้รู้ว่ามีคนแบบนั้นอยู่จริงๆ. | ดีใจที่ได้รู้ว่ามันมี | ดีใจที่รู้ว่าเขายังอยู่ |
| Der wird's schon bringen. Auch ohne uns Sünder. | เขาจะทำให้มันดีขึ้น | เขาจะทำได้แน่นอน. แม้จะไม่มีเราเป็นคนบาปด้วยก็ตาม. | เขาจะทําให้มันได้ แม้แต่ถ้าเราไม่ได้เป็นพวกบาป | เขาต้องทำได้แน่นอน แม้จะไม่มีเราคนบาป |
| Hoffe, er schafft's ins Finale. | หวังว่าเขาจะผ่านเข้ารอบสุดท้าย | หวังว่าเขาจะสามารถผ่านเข้าสู่รอบชิงชนะเลิศได้นะ. | หวังว่าเขาจะผ่านเข้ารอบ | หวังว่าเขาจะผ่านเข้าไปเล่นในรอบชิงชนะเลิศได้ |
| Nun denn, | เอาละ | เอาล่ะ… | ทีนี้ | แล้วล่ะ, |
| das wär's dann wohl. | นั่นก็คงจะดี | นั่นก็คงเป็นอย่างนั้นแหละ. | งั้นก็พอดีนะ | นั่นคงเป็นทั้งหมดแล้ว |
| Am Ende lief doch alles ganz gut für den Dude und Walter. | ท้ายที่สุดแล้วทุกอย่างก็ดี | ในท้ายที่สุดแล้ว ทุกอย่างก็เป็นไปได้ด้วยดีสำหรับเดวิดและวอลเตอร์. | ในที่สุด ทุกอย่างก็ดีมากสําหรับดุ๊ดและวอลเตอร์ | ท้ายที่สุดแล้ว ทุกอย่างก็จบลงด้วยดีสำหรับดูด์และวอลเตอร์ |
| 'Ne saubere, gute Geschichte, | 'Ne เรื่องที่ดีและสะอาด | ไม่ดีเลย… เรื่องราวที่แย่มากๆ | เรื่องที่ไม่สะอาดดี | เรื่องราวน่าสนใจและดีงาม |
| oder? | หรือ? | หรือไม่? | ใช่มั้ย? | หรือ? |
| Mußte oft brüllen vor Lachen. | ต้องกรีดร้องด้วยเสียงหัวเราะบ่อยๆ | มักจะต้องหัวเราะออกมาดังๆ เสมอ. | ต้องรีบตะโกนเพราะหัวเราะ | ต้องกรีดร้องด้วยความขบขันอยู่บ่อยครั้ง |
| Meistens jedenfalls. | ส่วนใหญ่แล้ว | โดยส่วนใหญ่แล้วก็เป็นอย่างนั้นแหละ. | อย่างน้อยก็เป็นส่วนใหญ่ | อย่างไรก็ตาม ส่วนใหญ่แล้ว |
| Gefiel mir nicht, daß Donny gehen mußte. | ฉันไม่ชอบมัน | ฉันไม่ชอบเลยที่โดนนี่ต้องจากไป… | ฉันไม่ชอบที่ดอนนี่ต้องไป | ฉันไม่ชอบที่ดอนนี่ต้องจากไป |
| Zufällig weiß ich aber, daß ein... | แต่โดยบังเอิญ ผมรู้ว่า... | แต่โดยบังเอิญ ฉันรู้ว่า… | แต่สิ่งที่ฉันรู้ก็คือ... | แต่โดยบังเอิญ ฉันรู้ว่ามี... |
| kleiner Lebowski unterwegs ist. | เลอบอสวิ่งไปมา | คลีนเนอร์ เลโบวสกี้กำลังอยู่ระหว่างการเดินทาง… | เลโบวสกี้ตัวเล็กกําลังเดินทาง | เมื่อเลบอฟสกี้ตัวน้อยออกเดินทาง |
| So setzt sich also die menschliche Komödie... | ดังนั้นการที่มนุษย์ | ดังนั้น การแสดงละครตลกของมนุษย์ก็จึงเป็นเช่นนี้เอง… | แล้วนี่คือเรื่องตลกของมนุษย์ | ดังนั้น มนุษย์จึงยังคงแสดงละครชีวิตต่อไป... |
| fort. | ต่อ | ป้อมปราการ | ไปเลย | ป้อม |
| Durch alle Generationen, | ผ่านทุกๆ รุ่น | ผ่านรุ่นต่างๆ มากมาย | ทั่วทุกรุ่น | ผ่านทุกยุคทุกสมัย |
| westwärts, | ไปทางทิศตะวันตก | ไปทางทิศตะวันตก. | ไปทางตะวันตก | ไปทางตะวันตก |
| über den Sand der Zeit bis... | ผ่านทรายของเวลาจนถึง... | บนผืนทรายแห่งกาลเวลา… | ผ่านทรายของเวลา จนกระทั่ง... | ผ่านทรายแห่งกาลเวลาจนถึง... |
| Ach je, | อ้า, | อ๊ะ… | ไม่เคย | โอ้ ไม่! |
| ich schweife schon wieder ab. | ฉันหลงทางอีกแล้ว | ฉันก็เริ่มเบี่ยงเบี้ยวจากเนื้อหาที่ต้องการจะพูดอีกแล้วนะ. | ฉันจะไปอีกแล้ว | ฉันกำลังออกนอกเรื่องอีกครั้งแล้ว |
| Macht's gut, Leute. | ทำดีๆนะทุกคน | ดีจังเลยนะ ทุกคน. | สบายนะเพื่อนๆ | นี่คือลำไส้ของมาคท์นะ folks |
| Ich sehe euch später. | ฉันจะเจอคุณทีหลังนะ | ฉันจะเจอพวกคุณในภายหลังนะ. | แล้วเจอกัน | ฉันจะพบพวกเธอทีหลัง |
| Guter Mann, | ผู้ชายที่ดี | ผู้ชายดีๆ นะ. | คุณชายดี | ผู้ชายที่ดี |
| kann ich noch 'nen Sarsaparilla haben? | ฉันยังสามารถ | ฉันยังมี ‘ซาร์ซาปาริลลา’ อีกไหม? | ขอซาร์ซาราปาริลล่าอีกหน่อยได้ไหม? | ฉันขอซาร์ซาพาริลลาอีกแก้วได้ไหม? |
| Untertitel: V. Maidit | คำบรรยาย: V. Maidit | ชื่อเรื่องย่อ: วี. มาดิต | ผู้เขียน หัวข้อ: V. Maidit | คำบรรยาย: V. Maidit |

Latency: gemmax2-2b: 3.0s/phrase | hymt15-18b: 3.5s/phrase | nllb600: 1.1s/phrase | qwen36-35b: 0.9s/phrase

## rus -> en (Russian to English)

| source | gemmax2-2b | hymt15-18b | nllb600 | qwen36-35b |
|---|---|---|---|---|
| И вообще, что ты городишь? | And in general, what are you talking about? | And anyway, what are you talking about? | What are you talking about, anyway? | And besides, what are you talking about? |
| Твою мать! | Holy Christ! | Damn it! | Oh, my God! | Damn it! |
| Чтоб тебя, Уолтер! - Замнем, Дюдя. | For you, Walter! | To you, Walter! – We’ll forget it, Dude. | - We're going to replace you, Judy. | Damn you, Walter! - We'll get you, Uncle. |
| Встряхнись, старина. | Wake up, old man. | Get up, old man. | Shake it up, old man. | Cheer up, old man. |
| Идем, идем. | Come on, come on. | Let’s go, let’s move on. | Let's go, let's go. | Let's go, let's go. |
| Пару пива, Гарри. - Момент. Удачи вам завтра! | A couple of beers, Harry. | A couple of beers, Harry. – Just a moment. Good luck tomorrow! | A couple of beers, Harry. | A couple of beers, Harry. - Hold on. Good luck tomorrow! |
| Спасибо. - С Донни нехорошо вышло. | Thank you. | Thank you. It didn’t go well with Donny. | - Donnie's not doing well. | Thank you. - It didn't go well with Donnie. |
| Точно. Что ж, бывает, ты ешь медведя, а бывает. . . | Well, sometimes you eat a bear, | Yes. Well, sometimes you eat a bear… And sometimes… | Well, sometimes you eat a bear, and sometimes... | Exactly. Well, sometimes you eat bear, and sometimes... |
| Эй, мужик! - Привет, Дюдя! | - Hey, man! | Hey, man! – Hi, Dudy! | - Hey, man, what's going on? | Hey, man! - Hi, Dudy! |
| Не думал, что свидимся. | I didn't think we'd meet. | I didn’t expect that we would meet again. | I didn't think we were seeing each other. | I didn't think we'd meet again. |
| Пропустить полуфинал? - И то. | Miss the semi-final? | Should we skip the semifinals? – Yes, that’s right. | - Miss the semi-finals? | Skip the semifinals? - Yeah, that's right. |
| Как вообще? - Так - то вверх, то вниз, то в полоску. | How is it at all? | How exactly? – It moves up, then down, and sometimes in strips. | - It's up, it's down, it's in the strip. | How is it going? - It's up, then down, then striped. |
| Понимаю. | I understand. | I understand. | Oh, I see. | I understand. |
| Да, спасибо, спасибо. Ну, счастливо. Мне пора. | Yes, thank you, thank you. | Yes, thank you, thank you. Well, I’m happy. It’s time for me to leave now. | Yeah, thank you, thank you. | Yes, thank you, thank you. Well, goodbye. I have to go. |
| Иди, не переживай. - Ага. | Come on, don't worry. | Go ahead, don’t worry about it. – Yeah. | Go on, don't worry about it. | Go ahead, don't worry. - Yeah. |
| Хотя знаю, ты и не будешь. - Само собой. Дюдя верен себе. | Although I know you won't. | Although I know that you won’t do it. – Of course not. Dudy is loyal to himself. | But I know you won't. | Although I know, you won't anyway. - Of course. Dudy is true to himself. |
| Уолтер! | Walter! | Walter! | Walter, what are you doing? | Walter! |
| Дюдя верен себе. | Dudu is true to himself. | Dudy is loyal to himself. | Dude is true to himself. | Dyadya is true to himself. |
| Не знаю, как вас, а меня это утешает. Приятно знать, что он, Дюдя, рядом. | I don't know about you, but it comforts me. | I don’t know about you, but it comforts me to know that he’s there, by his side. It’s nice to know that he’s with him, Dudy. | I don't know about you, but it's comforting to know he's around. | I don't know about you, but it comforts me. It's nice to know that he, Dudy, is nearby. |
| Не берет в голову за всех нас, грешных. Надеюсь, он пройдет в финал. | He doesn't take it to heart for all of us sinners. | He doesn’t care about all of us, sinners. I hope he will make it to the finals. | He doesn't care about all of us sinners, I hope he makes it to the finals. | He doesn't take it to heart for all of us, sinners. I hope he makes it to the finals. |
| Ну, вроде и все. Вот и развязка. | Well, that's it. That's the ending. | Well, it seems like everything is finally settled. That’s the end of this story. | Well, I guess that's it. | Well, that's about it. Here's the resolution. |
| У Дюди и Уолтера все более менее в порядке. | Dudy and Walter are increasingly less | In Dudy and Walter, everything is pretty much in order. | Dudie and Walter are getting less and less well. | Dude and Walter are more or less okay. |
| А ведь ничего история, согласны? Я ржал, как ненормальный, местами. | But it's not a story, right? | And it’s not even anything historical, right? I laughed like a madman, from time to time. | It's not a story, is it? | And it's quite a story, don't you agree? I was laughing like crazy in some parts. |
| А Донни, конечно, жаль. | And, of course, I feel sorry for Donny. | And Donny… well, it’s really sad. | Donnie, of course, is sorry. | And poor Donny, of course. |
| Зато, как я недавно слышал, маленький Лебовский на подходе. | On the other hand, as I recently heard, the little | But, as I heard recently, the little Lebowski is on his way there. | But, as I heard recently, little Lebovsky is on his way. | But, as I recently heard, the little Lebowski is on the way. |
| Так, собственно, и крутится человеческая комедия - за спиралью спираль, | So, in fact, the human | Yes, that’s exactly how human comedy operates – it revolves around a spiral of spirals. | So, actually, that's the human comedy behind the spiral, the spiral, | So, that's how the human comedy revolves—spiral after spiral, |
| . . .поколение за поколением, фургоны на запад через пески и годы пока. . . | ...generation after generation, the wagons on | …Generation after generation, trucks across the deserts and through the years… | . . .Generation after generation, vans to the west through the sands and years to the present. . . . | ...generation after generation, wagons heading west through the sands and years until... |
| Ну вот, опять меня понесло. Надеюсь, вы, ребята, не скучали. | Well, I'm off again. I hope | Well, I’m getting carried away again. I hope that you guys didn’t get bored during this time. | I hope you guys didn't miss it. | Well, here I go again. I hope you guys weren't bored. |
| Ну, как-нибудь пересечемся. | Well, we'll cross paths sometime. | Well, somehow we will definitely run into each other. | Well, I'll see you sometime. | Well, we'll cross paths sometime. |
| Гарри, еще осталась та чудная "Сарсо Парильо"? | Harry, there's still that wonderful | Harry, is that wonderful “Sarso Parillo” still around? | Harry, is there still that gorgeous Sarso Parrillo? | Harry, is there still that wonderful "Sarso Parillo" left? |

Latency: gemmax2-2b: 4.7s/phrase | hymt15-18b: 4.2s/phrase | nllb600: 1.6s/phrase | qwen36-35b: 1.4s/phrase

## rus -> de (Russian to German)

| source | gemmax2-2b | hymt15-18b | nllb600 | qwen36-35b |
|---|---|---|---|---|
| И вообще, что ты городишь? | Und was hast du überhaupt vor? | Und im Allgemeinen – was redest du da eigentlich? | Was willst du überhaupt? | Und überhaupt, was redest du da? |
| Твою мать! | Scheiße! | Deine Mutter! | Scheiße! | Scheiße! |
| Чтоб тебя, Уолтер! - Замнем, Дюдя. | - Für dich, Walter! | Um dich zu retten, Walter! – Wir werden es schaffen, Düdje. | - Wir werden dich ersetzen, Duddy. | Verdammt noch mal, Walter! - Wir beißen dich, Onkel. |
| Встряхнись, старина. | Mach dich auf, alter Mann. | Beruhige dich doch, alter Freund. | Schütteln Sie sich, Alter. | Rüttel dich, Alter. |
| Идем, идем. | Kommen Sie, kommen Sie. | Lass uns gehen. | Komm schon, komm schon. | Los geht's, los geht's. |
| Пару пива, Гарри. - Момент. Удачи вам завтра! | Ein paar Bier, Harry. | Eine Flasche Bier, Harry. – Moment. Viel Glück für Sie morgen! | Ein paar Bier, Harry. | Ein paar Biere, Harry. - Moment. Viel Glück morgen! |
| Спасибо. - С Донни нехорошо вышло. | Danke. | Danke. Es ist nicht gut gelaufen mit Donny. | - Das war nicht gut mit Donnie. | Danke. - Mit Donny ist etwas Schlimmes passiert. |
| Точно. Что ж, бывает, ты ешь медведя, а бывает. . . | Ja, ja, manchmal isst man einen Bären, | Genau. Es kommt vor, dass man einen Bären isst… Aber es gibt auch andere Möglichkeiten. | Genau. Nun, manchmal isst du einen Bären, und manchmal... | Genau. Nun ja, das kommt vor: Mal isst du Bär, und mal ... |
| Эй, мужик! - Привет, Дюдя! | Hey, Mann! | Hey, Mann! – Hallo, Düdya! | - Hey, Mann! | Hey, Kerl! - Hallo, Djudja! |
| Не думал, что свидимся. | Ich hätte nicht gedacht, dass wir uns treffen würden. | Ich hätte nicht gedacht, dass wir uns wiedersehen würden. | Ich dachte nicht, wir wären zusammen. | Ich hätte nicht gedacht, dass wir uns wiedersehen. |
| Пропустить полуфинал? - И то. | Halbfinale verpassen? | Sollte man das Halbfinale überspringen? – Ja. | - Soll ich das Halbfinale verpassen? | Halbfinale überspringen? - Das auch. |
| Как вообще? - Так - то вверх, то вниз, то в полоску. | Wie überhaupt? | Wie genau? – So – mal nach oben, mal nach unten, mal in Streifen. | - Auf, runter oder in die Strecke. | Wie ist das überhaupt? - Mal nach oben, mal nach unten, mal gestreift. |
| Понимаю. | Ich verstehe. | Ich verstehe. | Ich verstehe. | Verstehe. |
| Да, спасибо, спасибо. Ну, счастливо. Мне пора. | Ja, danke, danke. | Ja, danke, vielen Dank. Nun, ich muss jetzt gehen. | Ja, danke, danke. Ich muss gehen. | Ja, danke, danke. Nun, auf Wiedersehen. Ich muss gehen. |
| Иди, не переживай. - Ага. | Komm, mach dir keine Sorgen. | Geh einfach, mach dir keine Sorgen. – Ja. | - Gehen Sie, keine Sorgen. | Geh nur, mach dir keine Sorgen. - Ja. |
| Хотя знаю, ты и не будешь. - Само собой. Дюдя верен себе. | Ich weiß, dass du es nicht tun wirst. | Auch wenn ich weiß, dass du es nicht tun wirst… – Das ist selbstverständlich. Düdy bleibt immer treu zu sich selbst. | Ich weiß, du wirst es nicht tun. | Obwohl ich weiß, dass du es nicht tun wirst. - Natürlich. Djudja bleibt sich treu. |
| Уолтер! | Walter! | Walter! | Was ist los? | Walter! |
| Дюдя верен себе. | Dujia ist sich selbst treu. | Düdi ist loyal gegenüber sich selbst. | Dudja ist sich selbst treu. | Dudja bleibt sich treu. |
| Не знаю, как вас, а меня это утешает. Приятно знать, что он, Дюдя, рядом. | Ich weiß nicht, wie es Ihnen geht, aber es tröstet mich. | Ich weiß nicht, wie es Ihnen geht – aber für mich ist das eine Erleichterung. Es ist schön zu wissen, dass er, Düdya, in der Nähe ist. | Ich weiß nicht, wie es mit Ihnen geht, aber es ist schön zu wissen, dass er da ist. | Ich weiß nicht, wie es Ihnen geht, aber es tröstet mich. Es ist schön zu wissen, dass er, Djudja, in der Nähe ist. |
| Не берет в голову за всех нас, грешных. Надеюсь, он пройдет в финал. | Er nimmt nicht an, dass wir alle Sünder sind. | Er kümmert sich nicht um uns alle, die wir Sündige sind. Ich hoffe, dass er es ins Finale schafft. | Ich hoffe, er kommt ins Finale. | Er nimmt sich nicht die Mühe, für uns alle, die Sünder, nachzudenken. Ich hoffe, er schafft es ins Finale. |
| Ну, вроде и все. Вот и развязка. | Nun, so ist es. Das ist die Lösung. | Nun, anscheinend ist alles vorbei. Das war also die entscheidende Wendung. | Also, das ist alles. | Nun, das war's eigentlich. Hier ist die Auflösung. |
| У Дюди и Уолтера все более менее в порядке. | Dudy und Walter sind immer weniger | Bei Dudy und Walter ist alles mehr oder weniger in Ordnung. | Dudie und Walter sind immer weniger in Ordnung. | Bei Dudy und Walter ist alles mehr oder weniger in Ordnung. |
| А ведь ничего история, согласны? Я ржал, как ненормальный, местами. | Aber es ist doch nichts Historisches, stimmt? | Und doch ist das nichts Besonderes, oder? Ich habe gelacht, wie ein Verrückter – an manchen Stellen sogar ziemlich heftig. | Es ist doch keine Geschichte, okay? | Und dabei ist die Geschichte eigentlich ganz normal, oder? Ich habe mich stellenweise wie verrückt gekringt. |
| А Донни, конечно, жаль. | Und natürlich tut es Donny leid. | Und Donny… natürlich ist es schade. | Und Donnie, natürlich, tut mir leid. | Und Donny ist natürlich schade. |
| Зато, как я недавно слышал, маленький Лебовский на подходе. | Aber, wie ich kürzlich gehört habe, der kleine | Doch, wie ich kürzlich gehört habe, ist der kleine Lebowski bereits auf dem Weg dorthin. | Wie ich erst kürzlich gehört habe, kommt der kleine Lebowski. | Aber, wie ich kürzlich gehört habe, kommt der kleine Lebowski auf uns zu. |
| Так, собственно, и крутится человеческая комедия - за спиралью спираль, | So dreht sich die menschliche | Ja, genau so dreht sich auch die menschliche Komödie – hinter der Spirale der Spiralen. | Das ist eigentlich die menschliche Komödie. | So dreht sich im Grunde die menschliche Komödie – Spirale um Spirale, |
| . . .поколение за поколением, фургоны на запад через пески и годы пока. . . | ... Generation für Generation, die Furgonen auf | Generation für Generation – die Wagen auf dem Weg nach Westen, durch die Sanddünen und die Jahre… | . . .Generation für Generation, Waggons nach Westen durch den Sand und die Jahre bis dahin. . . . | . . . Generation um Generation, Lieferwagen nach Westen durch die Wüsten und die Jahre hindurch, bis . . . |
| Ну вот, опять меня понесло. Надеюсь, вы, ребята, не скучали. | Nun, ich bin wieder da. Ich hoffe, | Nun, wieder habe ich angefangen zu schreiben. Hoffentlich haben Sie, ihr Jungs, nicht gelitten. | Ich hoffe, ihr habt es nicht vermisst. | Na gut, ich habe mich wieder mal hinreißen lassen. Ich hoffe, ihr habt euch nicht langweilt. |
| Ну, как-нибудь пересечемся. | Na, wir werden uns irgendwann treffen. | Nun, irgendwann werden wir uns sicher wieder treffen. | Wir werden uns irgendwann treffen. | Na, wir werden uns schon irgendwie wiedersehen. |
| Гарри, еще осталась та чудная "Сарсо Парильо"? | Harry, da ist noch die wunderbare | Harry – es gibt immer noch diese wunderbare „Sarso Parillo“. | Harry, gibt's noch dieses wunderbare Parillo? | Harry, ist noch die wunderbare „Sarso Parillo“ übrig? |

Latency: gemmax2-2b: 4.8s/phrase | hymt15-18b: 4.8s/phrase | nllb600: 1.6s/phrase | qwen36-35b: 1.5s/phrase

## rus -> th (Russian to Thai)

| source | gemmax2-2b | hymt15-18b | nllb600 | qwen36-35b |
|---|---|---|---|---|
| И вообще, что ты городишь? | และโดยทั่วไปแล้ว คุณกำลังทำอะไรอยู่? | แล้วโดยทั่วไปแล้ว คุณกำลังพูดอะไรกันแน่ล่ะ? | แล้วคุณกําลังทําอะไรอยู่? | และโดยทั่วไปแล้ว คุณกำลังพูดอะไรอยู่น่ะ? |
| Твою мать! | แม่เจ้า | บ้าไปแล้ว! | ให้ตายสิ | แม่เอ๊ย! |
| Чтоб тебя, Уолтер! - Замнем, Дюдя. | - ให้เธอละ วอลเตอร์ | ขอให้เจ้าได้รับความสุขนะ วอลเตอร์! – เราจะทำเช่นนั้นเอง, ดุยดี้. | ให้ตาย วอลเตอร์! | - ไอ้วอลเตอร์! - อย่ามาพูดจาแบบนั้นสิ, ดิวดี |
| Встряхнись, старина. | ตื่นเถอะ แก่เฒ่า | ฟื้นตัวขึ้นมาเถอะ, คนแก่เอ๋ย. | โย่ย่าวาย | ปลุกตัวเองให้ตื่นขึ้นหน่อยนะ เพื่อนเก่า |
| Идем, идем. | ไปกันเถอะ ไปกันเถอะ | เราไปกันเถอะ. | ไปกันเถอะ | ไปกันเถอะ ไปกันเถอะ |
| Пару пива, Гарри. - Момент. Удачи вам завтра! | เบียร์สองขวดนะ แฮร์รี่ | เบียร์สองขวดนะ, แฮร์รี่… – ได้เลย… ขอให้คุณมีโชคดีในวันพรุ่งนี้นะ! | แฮร์รี่ ขอให้พรุ่งนี้โชคดี | เบียร์สองแก้วนะ แฮร์รี - รอสักครู่ ขอให้โชคดีในวันพรุ่งนี้! |
| Спасибо. - С Донни нехорошо вышло. | ขอบคุณ | ขอบคุณค่ะ. – การกระทำของโดนนี่ไม่ดีเลย. | - ดอนนี่ไม่ค่อยดี | ขอบคุณครับ - เรื่องของดอนนี่มันออกมาไม่ดีเลย |
| Точно. Что ж, бывает, ты ешь медведя, а бывает. . . | แน่นอน. อย่างไรก็ตาม, คุณกินหมี | ใช่แล้ว. บางครั้งเราก็กินหมีได้… แต่บางครั้งก็ไม่ได้หรอก. | ใช่แล้ว บางครั้งคุณกินหมี แต่บางครั้ง... | แน่นอนล่ะ บางครั้งก็เกิดเรื่องแบบนี้ขึ้น คุณกินเนื้อหมี แล้วบางครั้งก็... |
| Эй, мужик! - Привет, Дюдя! | - เฮ้, ชาย! | เฮ้ ไอ้หนุ่มเอ๋ย! – สวัสดีนะ ดูดี้! | สวัสดีครับ ดิวดา | เฮ้ย เพื่อน! - สวัสดี, ดูเดีย! |
| Не думал, что свидимся. | ไม่คิดว่าจะได้เจอกัน | ไม่คิดเลยว่าจะได้พบกันอีก… | ฉันไม่คิดว่าเราจะได้พบกัน | ฉันไม่คิดว่าจะได้พบกันอีก |
| Пропустить полуфинал? - И то. | พลาดรอบตัดเชือก? | ขอให้ผ่านเข้ารอบน็อกเอาต์ได้เลย… | จะพลาดรอบรองชนะเลิศเหรอ? | ข้ามรอบรองชนะเลิศไปเลย? - ก็ใช่สิ. |
| Как вообще? - Так - то вверх, то вниз, то в полоску. | มันเป็นยังไง? | อย่างไรกันล่ะ? – ก็ขึ้นไปบ้าง ลงมาบ้าง หรือเคลื่อนไหวเป็นแถวๆ บ้างเหมือนกัน. | - มันขึ้นไปข้างบน หรือลงไปข้างล่าง | เป็นยังไงบ้าง? - ก็ขึ้นๆ ลงๆ บางทีก็แบบเป็นทาง |
| Понимаю. | เข้าใจ | ฉันเข้าใจแล้ว. | ฉันเข้าใจ | เข้าใจ |
| Да, спасибо, спасибо. Ну, счастливо. Мне пора. | ขอบคุณ ขอบคุณ | ใช่ค่ะ ขอบคุณมากค่ะ. เอาล่ะ… ขอให้มีความสุขนะคะ. ฉันต้องไปแล้วค่ะ. | ใช่ ขอบใจ ขอบใจ ดีใจ ฉันจะไป | ใช่ครับ ขอบคุณครับ ขอบคุณมาก โอเค แล้วเจอกันนะครับ ผมต้องไปแล้ว |
| Иди, не переживай. - Ага. | - ไปเถอะ ไม่ต้องห่วง | ไปเถอะ ไม่ต้องกังวลเลย. – อืม. | ไปเถอะ ไม่ต้องกังวล | ไปเถอะ ไม่ต้องกังวล - ใช่ |
| Хотя знаю, ты и не будешь. - Само собой. Дюдя верен себе. | แม้ว่าฉันรู้ว่าคุณคงไม่ทำ | แม้ว่าฉันจะรู้ว่าเธอคงไม่ทำอย่างนั้นหรอก… – เป็นเรื่องที่เกิดขึ้นโดยธรรมชาติของคนแบบเขาเอง. | แต่ข้ารู้แล้วว่าเจ้าคงไม่เป็นแน่ แน่นอน ดิวดาเชื่อใจตัวเอง | แม้ฉันจะรู้ดีว่าเธอคงไม่ทำ -当然แล้ว ดิวเดียคงไม่เปลี่ยนไปจากเดิม |
| Уолтер! | วอลเตอร์! | วอลเตอร์! | วอลเตอร์! | วอลเตอร์! |
| Дюдя верен себе. | ดูดีจูดีมีสัจจะ | ดูดยานั้นซื่อสัตย์กับตัวเองมาก. | ดิวดาเชื่อมั่นกับตัวเอง | ดูเดียยังคงเป็นตัวของตัวเอง |
| Не знаю, как вас, а меня это утешает. Приятно знать, что он, Дюдя, рядом. | ไม่รู้ว่าคุณเป็นยังไง แต่ฉันรู้สึกสบายใจขึ้น | ไม่รู้ว่าคุณจะคิดอย่างไร แต่สำหรับฉันแล้ว นั่นเป็นเรื่องที่ช่วยให้ฉันรู้สึกดีขึ้นได้จริงๆ มันเป็นเรื่องที่น่ายินดีที่ได้รู้ว่าเขาอยู่ข้างๆ ฉัน… ดุยดา. | ฉันไม่รู้ว่าคุณเป็นอย่างไร แต่มันทําให้ฉันรู้สึกดีใจ | ไม่รู้ว่าสำหรับคุณแล้วเป็นอย่างไร แต่สำหรับฉันแล้วมันทำให้รู้สึกสบายใจ รู้สึกดีที่ได้รู้ว่าเขาอยู่ใกล้ๆ นั่นคือ ดิวเดีย |
| Не берет в голову за всех нас, грешных. Надеюсь, он пройдет в финал. | ไม่คิดว่ามันจะเกิดขึ้นกับพวกเราทุกคนที่เป็นคนบาป | เขาไม่ได้คำนึงถึงพวกเราทุกคนเลย… พวกเราทั้งหลายที่มีบาปอยู่ในใจ. หวังว่าเขาจะสามารถผ่านเข้ารอบสุดท้ายได้. | เขาไม่คิดเรื่องพวกเราที่ทําบาป ฉันหวังว่าเขาจะผ่านเข้ารอบ | ไม่ยอมคิดแทนเราทุกคนที่เป็นคนบาป หวังว่าเขาจะผ่านเข้ารอบชิงชนะเลิศ |
| Ну, вроде и все. Вот и развязка. | โอ้ นั่นแหละทั้งหมด นั่นคือจุดจบ | เอาล่ะ… ดูเหมือนว่าทุกอย่างจะเสร็จสิ้นแล้วนะ. นี่แหละคือจุดจบของเรื่องราวนี้. | ก็คงเป็นอย่างนี้แหละ | ก็ดูเหมือนจะจบแล้วล่ะ นี่ไงจุดจบ |
| У Дюди и Уолтера все более менее в порядке. | ดูดีและวอลเตอร์มากขึ้น | ในกรณีของดิวดี้และวอลเตอร์ ทุกอย่างก็ยังคงเป็นปกติอยู่. | ดูดีกับวอลเตอร์ไม่ค่อยดีดีเท่าไหร่ | ดูดีและวอลเตอร์ก็อยู่ในสภาพที่ค่อนข้างปกติ |
| А ведь ничего история, согласны? Я ржал, как ненормальный, местами. | แต่ก็ไม่ใช่เรื่องอะไรหรอกนะ, คุณเห็นด้วยไหม? | และจริงๆ แล้ว มันก็ไม่ใช่เรื่องราวอะไรเลยนะ… ใช่ไหม? ฉันหัวเราะออกมาอย่างบ้าๆ บอๆ… | ไม่เป็นเรื่องอะไรเลย ฉันกีฬากีฬากีฬากีฬา | แต่เรื่องมันก็ไม่มีอะไรน่าตื่นเต้นเลยใช่ไหมล่ะ? ฉันหัวเราะจนแทบบ้าไปเลยในบางช่วง |
| А Донни, конечно, жаль. | และแน่นอนว่าฉันเสียใจกับดอนนี่ | และโดนนี่… แน่นอนว่ามันเป็นเรื่องน่าเสียดายจริงๆ. | และดอนนี่ก็ต้องเสียใจ | และดอนนี่ก็น่าสงสารจริงๆ |
| Зато, как я недавно слышал, маленький Лебовский на подходе. | แต่ที่ฉันได้ยินเมื่อไม่นานมานี้ว่า | แต่จากที่ฉันได้ยินมาเมื่อไม่นานนี้ ดูเหมือนว่าลีโบฟสกี้จะอยู่ในระยะที่ใกล้ๆ แล้ว. | แต่เมื่อวานนี้ฉันได้ยินว่า เลบอฟสกี้ตัวเล็กกําลังเข้ามา | แต่เมื่อไม่นานมานี้ ฉันได้ยินมาว่า เลบอฟสกี้ตัวน้อยกำลังจะมาถึง |
| Так, собственно, и крутится человеческая комедия - за спиралью спираль, | ดังนั้น, ในความเป็นจริง, และหมุนรอบมนุษย์ | ใช่แล้ว… ชีวิตมนุษย์ก็เป็นเช่นนั้นแหละ… วนเวียนไปตามวงกลมต่างๆ. | และนั่นคือการแสดงความตลกของมนุษย์ | ดังนั้น มนุษย์จึงหมุนเวียนอยู่ในละครแห่งชีวิต - รอบแล้วรอบเล่า |
| . . .поколение за поколением, фургоны на запад через пески и годы пока. . . | . . .รุ่นต่อรุ่น รถบรรทุกที่ | …รุ่นหนึ่งหลังจากรุ่นอื่น…รถม้าเหล่านั้นขับไปทางทิศตะวันตก ผ่านทรายและปีเวลาหลายๆ ปี… | . . .รุ่นต่อรุ่น รถยนต์ไปตะวันตกผ่านทรายและปัจจุบัน | ...จากรุ่นสู่รุ่น รถตู้มุ่งหน้าไปทางตะวันตกผ่านทะเลทรายและกาลเวลา... |
| Ну вот, опять меня понесло. Надеюсь, вы, ребята, не скучали. | โอ้, ฉันก็หลงไปอีกแล้วละ ฉันหวังว่า | อืม… ฉันก็ยังคงพูดออกมาอีกครั้งนะ… หวังว่าพวกคุณทุกคนจะไม่เบื่อกันนะ. | ฉันหวังว่าพวกคุณคงไม่คิดถึง | โอเค ตอนนี้ฉันก็เริ่มพูดเยอะอีกแล้ว หวังว่าพวกคุณจะไม่เบื่อจนเกินไปนะ |
| Ну, как-нибудь пересечемся. | โอ้ ฉันจะข้ามไปที่นั่น | เอาเป็นว่า เราคงจะได้พบกันอีกสักวันหนึ่งแน่นอน. | งั้นเราจะได้เจอกันสักวัน | ว่าแต่ เดี๋ยวค่อยมาเจอกันอีกทีก็แล้วกัน |
| Гарри, еще осталась та чудная "Сарсо Парильо"? | แฮร์รี่ ยังเหลืออีก | แฮร์รี่… ยังมี “ซาร์โซ ปาริโล” อีกหนึ่งคนที่น่าทึ่งอยู่เลย… | แฮร์รี่ ยังมีซาร์โซ ปารีลโล่อีกมั้ย | ฮารรี, ยังเหลือ “ซาร์โซ ปาร์ริโย” ที่ยอดเยี่ยมอยู่ใช่ไหม? |

Latency: gemmax2-2b: 4.8s/phrase | hymt15-18b: 6.2s/phrase | nllb600: 1.5s/phrase | qwen36-35b: 1.5s/phrase

## Latency summary (s/phrase average)

| pair | gemmax2-2b | hunyuan-mt-7b | hymt15-18b | hymt15-7b | madlad3b | milmmt-12b | nllb600 | qwen3-4b | qwen36-35b | seed-x-7b | tower-plus-9b | typhoon-15-4b |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| eng->de | 3.8 | 17.2 | 3.7 | 9.6 | 72.1 | 18.1 | 1.4 | 10.1 | 1.1 | 9.0 | 30.3 |  |
| eng->ru | 3.8 |  | 3.8 |  |  |  | 2.2 |  | 1.1 |  |  |  |
| eng->th | 4.1 |  | 5.8 |  |  |  | 1.5 |  | 1.0 |  |  | 8.8 |
| deu->en | 3.3 |  | 2.7 |  |  |  | 1.2 |  | 0.8 |  |  |  |
| deu->ru | 3.1 |  | 3.2 |  |  |  | 1.2 |  | 0.9 |  |  |  |
| deu->th | 3.0 |  | 3.5 |  |  |  | 1.1 |  | 0.9 |  |  |  |
| rus->en | 4.7 |  | 4.2 |  |  |  | 1.6 |  | 1.4 |  |  |  |
| rus->de | 4.8 |  | 4.8 |  |  |  | 1.6 |  | 1.5 |  |  |  |
| rus->th | 4.8 |  | 6.2 |  |  |  | 1.5 |  | 1.5 |  |  |  |
