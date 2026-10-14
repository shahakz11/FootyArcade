/**
 * Playmaker - Multi-Language Outreach Automation & Bounce Monitor
 * Bound to Google Spreadsheet: 1ZNJ57i7kVUYrdW4q4S3lRe4NqYUM7-lL4RQtSzX0_8Q
 */

const OUTREACH_TAB_ES = "Outreach - Spanish";
const OUTREACH_TAB_EN = "Outreach - English";
const SENDER_NAME = "Playmaker Team";
const SPREADSHEET_ID = "1ZNJ57i7kVUYrdW4q4S3lRe4NqYUM7-lL4RQtSzX0_8Q";

/**
 * Returns active spreadsheet or opens via ID fallback
 */
function getTargetSpreadsheet() {
  try {
    const active = SpreadsheetApp.getActiveSpreadsheet();
    if (active) return active;
  } catch (e) {}
  return SpreadsheetApp.openById(SPREADSHEET_ID);
}

const HEADERS = [
  "Status",
  "Company / Entity",
  "Category",
  "Recipient Email",
  "Fallback Channel",
  "Fallback URL / Handle",
  "Subject",
  "Email Body",
  "Sent Timestamp",
  "Notes / Log"
];

// SPANISH PROSPECTS WITH VERIFIED FALLBACKS
const SPANISH_LEADS = [
  {
    company: "Biwenger (Diario AS)",
    category: "Fantasy Football",
    email: "contacto@biwenger.com",
    fallbackChannel: "Web Form / Twitter DM",
    fallbackUrl: "https://www.biwenger.com/contacto/ (o Twitter: @biwenger)",
    subject: "Mini-juegos de fútbol diarios para Biwenger: Retención entre jornadas y tiempo de sesión",
    body: "Hola equipo de Biwenger,\n\nEn Biwenger tienen la mayor comunidad fantasy de LaLiga en España, pero como toda plataforma fantasy, existe el reto de mantener a los usuarios entrando a la app de lunes a jueves cuando no hay partidos en juego.\n\nDesarrollamos Playmaker (https://playmaker.best/es/), una suite de mini-juegos diarios de fútbol basados en datos estadísticos y de mercado: Top Fichajes, Cadena de Jugadores, Jugó Con, Destino de Fichaje y Pasaporte FC.\n\nNuestros juegos encajan de forma natural con el perfil de usuario de Biwenger, que analiza constantemente trayectorias y fichajes. Podríamos ofrecerles:\n1. Widget o sección in-app \"El Reto del Día\": Embebido sin fricción ni coste de desarrollo para ustedes.\n2. Gamificación entre jornadas: Los usuarios pueden jugar a diario para ganar créditos/trofeos fantasy o competir con los miembros de su propia liga.\n3. Cero mantenimiento: La actualización de datos y retos diarios se procesa de forma autónoma.\n\nPueden probar los retos en vivo aquí: https://playmaker.best/es/\n\n¿Tendrían 5 minutos esta semana para explorar una colaboración o piloto conjunto?\n\nUn saludo cordial,\n\nPlaymaker Team\nhttps://playmaker.best"
  },
  {
    company: "Mister Fantasy (Champion Games)",
    category: "Fantasy Football",
    email: "marc@championgames.com",
    fallbackChannel: "Help Center / Twitter DM",
    fallbackUrl: "https://mister.mundodeportivo.com (o Twitter: @mister_fantasy)",
    subject: "Gamificación diaria para Mister Fantasy: Mini-juegos de retención entre jornadas",
    body: "Hola Marc,\n\nTe escribo porque sigo el desarrollo de Mister Fantasy y la experiencia tan cuidada que han creado para los managers de fútbol.\n\nDesarrollamos Playmaker (https://playmaker.best/es/), un arcade de mini-juegos diarios de fútbol tipo Wordle pero basados en datos reales de mercado y carreras de futbolistas (Top Fichajes, Cadena de Jugadores, Jugó Con, Destino de Fichaje y Pasaporte FC).\n\nEl usuario de Mister Fantasy es precisamente el perfil que más disfruta recordando traspasos y compañeros de equipo. Pensamos que integrar un módulo o webview de \"Desafío del Día\" dentro de Mister Fantasy aportaría:\n- Un incentivo diario para abrir la app de lunes a viernes (reduciendo el valle de actividad entre jornadas).\n- Mayor tiempo de sesión por usuario activo.\n- Integración llave en mano, sin carga técnica para su equipo de desarrollo.\n\nPueden probar los modos de juego directamente en https://playmaker.best/es/\n\n¿Te interesaría que tengamos una breve llamada de 10 minutos para ver si tiene encaje para la app?\n\nUn saludo,\n\nPlaymaker Team\nhttps://playmaker.best"
  },
  {
    company: "FútbolFantasy",
    category: "Alineaciones & Fantasy",
    email: "futbolfantasy@gmail.com",
    fallbackChannel: "Web Form",
    fallbackUrl: "https://www.futbolfantasy.com/contacto",
    subject: "Widget de juegos interactivos de fútbol para FútbolFantasy (dwell time y engagement)",
    body: "Hola equipo de FútbolFantasy,\n\nFútbolFantasy es la web de referencia absoluta para quienes seguimos LaLiga y el fantasy a diario. Sus usuarios pasan mucho tiempo leyendo previas y posibles alineaciones.\n\nDesarrollamos Playmaker (https://playmaker.best/es/), una colección de mini-juegos diarios de fútbol basados en estadísticas y traspasos (Top Fichajes, Cadena de Jugadores, Jugó Con, Pasaporte FC).\n\nIntegrar un widget responsive de Playmaker en los laterales o al final de los artículos de FútbolFantasy permitiría:\n- Aumentar el tiempo medio de permanencia en página (dwell time), beneficiando directamente el rendimiento publicitario (RPM) y el SEO.\n- Dar a sus lectores un juego diario gratuito y rápido relacionado con el club del que están consultando la previa.\n- Cero mantenimiento: el contenido se actualiza automáticamente cada día.\n\nPueden ver el funcionamiento de los juegos aquí: https://playmaker.best/es/\n\n¿Les gustaría probar un widget piloto para ver cómo reacciona su audiencia?\n\nUn saludo cordial,\n\nPlaymaker Team\nhttps://playmaker.best"
  },
  {
    company: "Jornada Perfecta",
    category: "Fantasy & Noticias",
    email: "jornadaperfecta@gmail.com",
    fallbackChannel: "Web Form",
    fallbackUrl: "https://www.jornadaperfecta.com/blog/contacto/",
    subject: "Colaboración interactiva para Jornada Perfecta: Reto diario de fútbol",
    body: "Hola equipo de Jornada Perfecta,\n\nSeguimos de cerca sus análisis y guías fantasy para managers en España.\n\nDesarrollamos Playmaker (https://playmaker.best/es/), una suite de mini-juegos de fútbol diarios basados en estadísticas reales (Top Fichajes, Cadena de Jugadores, Jugó Con, Destino de Fichaje y Pasaporte FC).\n\nCreemos que un widget con \"El Reto del Día\" en su portal o recomendado en su boletín encajaría perfectamente con sus seguidores, incentivando visitas diarias incluso entre semana.\n\nPueden probar los juegos aquí: https://playmaker.best/es/\n\n¿Tendrían unos minutos para ver si les encaja probarlo juntos?\n\nUn saludo cordial,\n\nPlaymaker Team\nhttps://playmaker.best"
  },
  {
    company: "Comunio España",
    category: "Fantasy Football",
    email: "info@comunio.es",
    fallbackChannel: "Twitter DM",
    fallbackUrl: "https://twitter.com/comunioEs",
    subject: "Gamificación y mini-juegos diarios de fútbol para Comunio",
    body: "Hola equipo de Comunio,\n\nComunio es la plataforma histórica por excelencia para ligas de amigos en el fútbol español.\n\nDesarrollamos Playmaker (https://playmaker.best/es/), una plataforma de retos de lógica y memoria futbolera diaria (Top Fichajes, Cadena de Jugadores, Jugó Con, Pasaporte FC).\n\nNos encantaría explorar una integración ligera para que los miembros de las comunidades puedan competir a diario en un reto de fútbol rápido entre jornadas, fomentando la actividad en la plataforma de lunes a viernes.\n\nPueden ver los modos de juego en directo en https://playmaker.best/es/\n\n¿Sería posible coordinar unos minutos para comentarlo?\n\nUn saludo cordial,\n\nPlaymaker Team\nhttps://playmaker.best"
  },
  {
    company: "BeSoccer / Resultados de Fútbol",
    category: "Scores & Datos (España)",
    email: "api@besoccer.com",
    fallbackChannel: "Sponsorships / Advertising Email",
    fallbackUrl: "sponsoring@besoccer.com / salesteam@besoccer.com",
    subject: "Propuesta interactiva para BeSoccer: Mini-juegos diarios de fútbol integrables",
    body: "Hola equipo de BeSoccer,\n\nConocemos el ecosistema de BeSoccer y la enorme base de datos con la que alimentan a millones de aficionados tanto en España como en Latinoamérica.\n\nHemos desarrollado Playmaker (https://playmaker.best/es/), una plataforma de retos diarios de conocimiento futbolístico basados en datos históricos (Top Fichajes, Cadena de Jugadores, Pasaporte FC, Jugó Con).\n\nDado el perfil de aficionado que entra a BeSoccer a consultar estadísticas, fichajes y resultados, una colaboración para integrar un módulo de mini-juegos dentro de su web o app aportaría:\n- Mayor recurrencia diaria y aumento del tiempo medio por sesión.\n- Una experiencia interactiva ligera y responsive, adaptable como widget o marca compartida.\n- Posibilidad de patrocinar el reto diario con sus propios anunciantes.\n\nPueden ver los juegos en funcionamiento aquí: https://playmaker.best/es/\n\n¿Con quién de su equipo de producto o alianzas podríamos conversar unos minutos para valorar esta opción?\n\nUn saludo cordial,\n\nPlaymaker Team\nhttps://playmaker.best"
  },
  {
    company: "Promiedos",
    category: "Scores & Tablas (Argentina)",
    email: "contact@promiedos.com.ar",
    fallbackChannel: "Twitter DM / Instagram",
    fallbackUrl: "https://twitter.com/Promiedos (o Instagram: @promiedosok)",
    subject: "Juego futbolero diario para Promiedos (Reto del Día)",
    body: "Hola gente de Promiedos,\n\nTodos los que amamos el fútbol entramos a Promiedos a mirar las tablas, los historiales y los resultados al minuto.\n\nCreamos Playmaker (https://playmaker.best/es/), una web ligera y sin rodeos de desafíos diarios de fútbol pensada para verdaderos fanáticos:\n- Top Fichajes (adivinar los pases récord por club/nacionalidad).\n- Cadena de Jugadores (adivinar al jugador uniendo los clubes de su carrera).\n- Jugó Con (adivinar al futbolista misterioso por sus compañeros de cancha).\n- Pasaporte FC (desbloquear nacionalidades por club).\n\nSabemos que la comunidad de Promiedos es la más futbolera de todas y discute cada dato en los comentarios. Nos encantaría ofrecerles un widget o enlace integrable estilo \"El Juego del Día de Promiedos\", completamente gratuito, ultra-rápido y sin complicaciones técnicas.\n\nPueden probar los juegos acá: https://playmaker.best/es/\n\nSi les copa la idea, avísennos y charlamos cómo armarlo.\n\nAbrazo grande,\n\nPlaymaker Team\nhttps://playmaker.best"
  },
  {
    company: "Relevo (Vocento)",
    category: "Medio Deportivo (España)",
    email: "publi@relevo.com",
    fallbackChannel: "Redacción Email / Twitter DM",
    fallbackUrl: "redaccion@relevo.com (o Twitter: @relevo)",
    subject: "Propuesta interactiva para Relevo: Mini-juegos diarios de fútbol (retención y comunidad)",
    body: "Hola equipo de Relevo,\n\nNos encanta el tono fresco y la forma visual e interactiva con la que conectan con los aficionados en Relevo.\n\nPor eso queríamos presentarles Playmaker (https://playmaker.best/es/): un arcade de pasatiempos diarios de fútbol estilo Wordle, diseñado con una estética moderna e impulsado por datos reales (Top Fichajes, Cadena de Jugadores, Jugó Con, Pasaporte FC, Destino de Fichaje).\n\nCreemos que encaja con la identidad de Relevo para crear una sección de \"El Pasatiempo de Relevo\":\n- Fomenta la conversación y el debate en redes y comentarios cada mañana.\n- Aumenta el tiempo de permanencia en página de los lectores.\n- Integrable de forma inmediata vía iframe responsive o co-branding, con cero carga técnica para su redacción.\n\nPueden probar los juegos en directo aquí: https://playmaker.best/es/\n\n¿Tendrían unos minutos esta semana para ver si tiene encaje para su sección digital o redes?\n\nUn saludo cordial,\n\nPlaymaker Team\nhttps://playmaker.best"
  },
  {
    company: "Revista Panenka",
    category: "Cultura & Revista (España)",
    email: "publicidad@panenka.org",
    fallbackChannel: "Twitter DM / Editorial",
    fallbackUrl: "https://twitter.com/RevistaPanenka (o redaccion@panenka.org)",
    subject: "Colaboración interactiva para Panenka: Pasatiempos diarios de cultura y memoria futbolera",
    body: "Hola equipo de Panenka,\n\nPanenka es el hogar de la memoria y la cultura futbolera en nuestro idioma.\n\nDesarrollamos Playmaker (https://playmaker.best/es/), una plataforma de retos diarios donde el valor no está en adivinar marcadores, sino en recordar la historia del juego: trayectorias de futbolistas de culto, fichajes históricos (Top Fichajes), conexiones entre clubes (Cadena de Jugadores) y compañeros de equipo de época (Jugó Con).\n\nCreemos que un módulo interactivo diario en su web o newsletter encajaría con el paladar del lector de Panenka, ofreciendo un pasatiempo diario que pone a prueba la memoria futbolera sin publicidad invasiva ni fricción.\n\nPueden ver cómo funciona en https://playmaker.best/es/\n\n¿Les gustaría que intercambiemos impresiones sobre cómo colaborar?\n\nUn saludo cordial,\n\nPlaymaker Team\nhttps://playmaker.best"
  },
  {
    company: "ElDesmarque (Mediaset)",
    category: "Medio Deportivo (España)",
    email: "redaccion@eldesmarque.com",
    fallbackChannel: "Twitter DM",
    fallbackUrl: "https://twitter.com/eldesmarque",
    subject: "Módulo de mini-juegos de fútbol para ElDesmarque: Incremento de tiempo en página",
    body: "Hola equipo de ElDesmarque,\n\nNos ponemos en contacto para presentarles una propuesta orientada a enriquecer la experiencia de sus lectores y maximizar el tiempo medio por visita (dwell time) en ElDesmarque.\n\nDesarrollamos Playmaker (https://playmaker.best/es/), una suite de mini-juegos diarios de fútbol basados en datos oficiales (Top Fichajes, Cadena de Jugadores, Jugó Con, Pasaporte FC, Destino de Fichaje).\n\nPara un medio con el volumen y la cobertura club a club de ElDesmarque, integrar un widget interactivo diario ofrece ventajas inmediatas:\n- Aumenta sensiblemente el tiempo de permanencia en la página del artículo.\n- Genera un hábito de regreso diario en los lectores de cada equipo.\n- Es 100% responsive, ligero y autónomo (no requiere intervención de su redacción ni infraestructura de servidores).\n\nPueden probar los juegos en directo aquí: https://playmaker.best/es/\n\n¿Con qué persona de su equipo digital o de producto podríamos valorar una prueba piloto?\n\nUn saludo cordial,\n\nPlaymaker Team\nhttps://playmaker.best"
  },
  {
    company: "Futbol Sites / Bolavip",
    category: "Red de Medios (LatAm)",
    email: "contact@futbolsites.net",
    fallbackChannel: "Web Form",
    fallbackUrl: "https://bolavip.com/info/contact",
    subject: "Propuesta de Gamificación para la red de Futbol Sites (Bolavip, RedGol): Mini-juegos diarios",
    body: "Hola equipo de Futbol Sites,\n\nConocemos el alcance de su red de medios deportivos en América Latina y el mercado hispano de Estados Unidos (Bolavip, RedGol, DaleAlbo, etc.).\n\nHemos desarrollado Playmaker (https://playmaker.best/es/), una plataforma de juegos diarios de trivia y lógica futbolera basados en datos (Top Fichajes, Cadena de Jugadores, Jugó Con, Pasaporte FC).\n\nLos formatos de daily mini-games han demostrado ser una de las herramientas más efectivas para generar hábitos de retorno diario y elevar el tiempo de permanencia (dwell time) en portales deportivos de alto tráfico.\n\nPodemos ofrecerles:\n- Módulos web embebibles o secciones co-brandeadas para sus portales regionales.\n- Posibilidad de patrocinar los retos diarios con las marcas y casas de apuestas aliadas de su red.\n- Integración llave en mano sin sobrecargar a sus equipos de ingeniería.\n\nPueden ver la plataforma en vivo aquí: https://playmaker.best/es/\n\n¿Podríamos coordinar una breve llamada de 10 minutos con su equipo de alianzas o producto digital?\n\nUn saludo cordial,\n\nPlaymaker Team\nhttps://playmaker.best"
  },
  {
    company: "Somos Invictos",
    category: "Comunidad & Medios (México/LatAm)",
    email: "contacto@somosinvictos.com",
    fallbackChannel: "Web Form / Twitter DM",
    fallbackUrl: "https://somosinvictos.com/contactanos/ (o Twitter: @SomosInvictos)",
    subject: "Dinámica diaria interactiva para la comunidad de Somos Invictos",
    body: "Hola equipo de Somos Invictos,\n\nSeguimos a diario el contenido y los debates que generan con la comunidad futbolera más apasionada de redes.\n\nCreamos Playmaker (https://playmaker.best/es/), una suite de retos diarios donde los aficionados ponen a prueba cuánto saben de fútbol internacional:\n- Top Fichajes (adivinar las compras récord por equipo o país).\n- Cadena de Jugadores (adivinar al jugador uniendo los clubes de su carrera).\n- Jugó Con (adivinar al futbolista misterioso por los compañeros con los que compartió cancha).\n- Pasaporte FC y Destino de Fichaje.\n\nCreemos que una sección de \"El Reto del Día\" en su web o impulsada en sus canales generaría una interacción masiva, debates diarios en comentarios y una razón más para que la gente entre a su sitio todos los días.\n\nPueden probar los retos en vivo acá: https://playmaker.best/es/\n\n¿Qué les parece si exploramos una colaboración sencilla para su audiencia?\n\nUn saludo cordial,\n\nPlaymaker Team\nhttps://playmaker.best"
  },
  {
    company: "JuanFutbol",
    category: "Medio Joven (México)",
    email: "hey@juanfutbol.com",
    fallbackChannel: "Twitter DM",
    fallbackUrl: "https://twitter.com/juanfutbol",
    subject: "Retos futboleros diarios para la comunidad de JuanFutbol",
    body: "Hola compas de JuanFutbol,\n\nUstedes tienen la vibra más entretenida y cercana del fútbol digital en México y Latinoamérica.\n\nDesarrollamos Playmaker (https://playmaker.best/es/), una plataforma de mini-juegos diarios de fútbol al estilo Wordle pero con sabor futbolero puro: Top Fichajes, Cadena de Jugadores, Jugó Con y Pasaporte FC.\n\nCreemos que armar una colaboración para que JuanFutbol tenga su propio \"Desafío del Día\" o embeber los juegos en su portal sería un hitazo para su comunidad: engancha en 2 minutos, genera piques en redes y hace que la gente vuelva cada mañana.\n\nPueden echarle un ojo a los juegos aquí: https://playmaker.best/es/\n\n¿Les late que platiquemos 5 minutos para ver cómo podemos armar algo juntos?\n\nUn saludo,\n\nPlaymaker Team\nhttps://playmaker.best"
  },
  {
    company: "La Media Inglesa",
    category: "Comunidad & YouTube (España)",
    email: "info@lamediainglesa.com",
    fallbackChannel: "YouTube About Email / Twitter DM",
    fallbackUrl: "https://twitter.com/LaMediaInglesa",
    subject: "Pasatiempo futbolero diario para la comunidad de La Media Inglesa",
    body: "Hola equipo de La Media Inglesa,\n\nSabemos lo mucho que disfruta su comunidad con los debates de historia, transferencias y anécdotas de jugadores en cada directo y video.\n\nDesarrollamos Playmaker (https://playmaker.best/es/), una plataforma de desafíos diarios de memoria futbolera basada en datos reales:\n- Cadena de Jugadores (unir clubes de una trayectoria).\n- Jugó Con (adivinar al jugador a partir de 5 compañeros con los que compartió vestuario).\n- Top Fichajes (los fichajes más caros por club/nacionalidad).\n- Pasaporte FC (sellos progresivos de nacionalidades).\n\nPensamos que integrar o recomendar un reto diario en su web o comunidad sería un complemento perfecto para que sus seguidores pongan a prueba su conocimiento futbolístico cada día.\n\nPueden probar los juegos en directo aquí: https://playmaker.best/es/\n\n¿Les gustaría que conversemos brevemente sobre posibles formas de colaborar?\n\nUn saludo cordial,\n\nPlaymaker Team\nhttps://playmaker.best"
  }
];

// ENGLISH PROSPECTS WITH VERIFIED FALLBACKS
const ENGLISH_LEADS = [
  {
    company: "FotMob",
    category: "Scores & Stats App (Global)",
    email: "sales@fotmob.com",
    fallbackChannel: "Web Form / LinkedIn",
    fallbackUrl: "https://fotmob.com/contact",
    subject: "Daily Interactive Football Mini-Games for FotMob (Mid-Week User Retention)",
    body: "Hi FotMob Partnerships Team,\n\nFotMob provides the cleanest match stats experience in world football. However, sports media apps always face the mid-week lull when no major fixtures are playing.\n\nWe built Playmaker (https://playmaker.best), an arcade of daily football knowledge games powered by verified transfer and career data:\n- Top Transfers (guess record signings by club & nationality)\n- Player Chain (connect clubs along a mystery player's career path)\n- Played With (guess the star by uncovering teammates ranked by appearances together)\n- Passport FC & Transfer Destination\n\nDaily games provide a natural habit loop that brings users into the app every morning. We can provide:\n1. A lightweight, responsive webview / widget module with zero engineering overhead for FotMob.\n2. Co-branded styling and sponsored challenge integration for your commercial partners.\n3. Fully automated daily updates.\n\nYou can test today's live puzzles here: https://playmaker.best\n\nWould someone on your partnerships or product team be open to a quick 10-minute chat?\n\nBest regards,\n\nPlaymaker Team\nhttps://playmaker.best"
  },
  {
    company: "Fantasy Football Scout",
    category: "Fantasy Premier League",
    email: "support@fantasyfootballscout.co.uk",
    fallbackChannel: "Twitter DM",
    fallbackUrl: "https://twitter.com/FFScout",
    subject: "Interactive Daily Football Puzzles for Fantasy Football Scout",
    body: "Hi Fantasy Football Scout Team,\n\nFFScout is the definitive home for FPL managers looking for statistical edges. Fantasy managers have an obsessive memory for player transfers and team history.\n\nWe built Playmaker (https://playmaker.best), a collection of daily football puzzle games (Top Transfers, Player Chain, Played With, Passport FC).\n\nEmbedding a \"Daily Teaser\" widget on FFScout articles during international breaks or mid-week lulls:\n- Drives measurable increases in average dwell time (boosting ad RPMs).\n- Provides an engaging daily challenge for your community.\n- Requires zero developer maintenance.\n\nYou can play today's live challenges at https://playmaker.best\n\nCould we explore a quick pilot or partnership for your readership?\n\nBest regards,\n\nPlaymaker Team\nhttps://playmaker.best"
  },
  {
    company: "Fantasy Football Hub",
    category: "Fantasy Premier League",
    email: "support@fantasyfootballhub.co.uk",
    fallbackChannel: "Web Support Chat",
    fallbackUrl: "https://www.fantasyfootballhub.co.uk",
    subject: "Turnkey Daily Football Mini-Games for Fantasy Football Hub",
    body: "Hi Fantasy Football Hub Team,\n\nYour suite of FPL AI and planning tools is top-tier. To complement your tools between gameweeks, we'd love to propose an interactive content integration.\n\nPlaymaker (https://playmaker.best) offers free daily football trivia puzzles based on player transfers and career paths (Top Transfers, Player Chain, Played With).\n\nIntegrating a lightweight daily mini-game gives members another reason to log in every morning throughout the week.\n\nYou can preview the challenges live at: https://playmaker.best\n\nWould you be open to a brief chat to see how we could integrate this for Hub members?\n\nBest regards,\n\nPlaymaker Team\nhttps://playmaker.best"
  },
  {
    company: "Football365 (Planet Sport)",
    category: "Digital Football Media (UK)",
    email: "theeditor@football365.com",
    fallbackChannel: "Commercial Email / Web Form",
    fallbackUrl: "info@planetsport.com / https://www.planetsport.com/contact",
    subject: "Interactive Daily Football Puzzles for Football365 (Dwell Time & Engagement)",
    body: "Hi Football365 Editorial Team,\n\nFootball365 has long been home to the sharpest debate and opinion in football journalism.\n\nWe built Playmaker (https://playmaker.best), a fast, mobile-first suite of daily football puzzles designed like Wordle (Top Transfers, Player Chain, Played With, Passport FC).\n\nSimilar to how major publishers leverage daily games for reader retention, an embeddable Playmaker widget on F365 would:\n- Significantly increase average time-on-page.\n- Spark daily debate in mailbox and comments.\n- Run autonomously with zero editorial burden.\n\nYou can test the puzzles live here: https://playmaker.best\n\nWould you have 5 minutes to discuss a content trial?\n\nBest regards,\n\nPlaymaker Team\nhttps://playmaker.best"
  },
  {
    company: "Squawka",
    category: "Football Stats & Gaming (UK)",
    email: "support@squawka.com",
    fallbackChannel: "Twitter DM",
    fallbackUrl: "https://twitter.com/Squawka",
    subject: "Daily Data-Driven Football Mini-Games for Squawka",
    body: "Hi Squawka Team,\n\nSquawka has pioneered football data visualization and fan engagement for years.\n\nWe created Playmaker (https://playmaker.best), an arcade of daily football knowledge games powered by verified historical data (Top Transfers, Player Chain, Played With, Passport FC).\n\nSquawka readers live and breathe stats. A daily embedded puzzle on your portal would drive substantial recurring engagement and social sharing among your stat-loving audience.\n\nCheck out the live platform here: https://playmaker.best\n\nCould we connect with your product or commercial team to discuss an integration?\n\nBest regards,\n\nPlaymaker Team\nhttps://playmaker.best"
  },
  {
    company: "This Is Anfield",
    category: "Club Fan Media (Liverpool FC)",
    email: "thisisanfield@thisisanfield.com",
    fallbackChannel: "Twitter DM",
    fallbackUrl: "https://twitter.com/thisisanfield",
    subject: "Interactive Daily Football Quizzes for This Is Anfield Readers",
    body: "Hi This Is Anfield Team,\n\nThis Is Anfield is the premier independent community for Liverpool supporters worldwide.\n\nWe developed Playmaker (https://playmaker.best), a suite of daily football challenges (including club-specific transfer trivia, teammate guessers, and player chains).\n\nWe can provide an embeddable, customized \"Daily Liverpool / Football Teaser\" for your site to boost reader dwell time and repeat visits between match fixtures.\n\nYou can try the live challenges at: https://playmaker.best\n\nWould you be open to testing a pilot widget for your readers?\n\nBest regards,\n\nPlaymaker Team\nhttps://playmaker.best"
  },
  {
    company: "Sofascore",
    category: "Live Scores & Ratings (Global)",
    email: "partnerships@sofascore.com",
    fallbackChannel: "Corporate Form / Advertising",
    fallbackUrl: "advertising@sofascore.com / https://corporate.sofascore.com/contact",
    subject: "Daily Interactive Football Mini-Games for Sofascore (User Retention)",
    body: "Hi Sofascore Partnerships Team,\n\nSofascore is the global leader in player ratings and statistical depth.\n\nWe built Playmaker (https://playmaker.best), a turnkey arcade of daily football knowledge games:\n- Top Transfers\n- Player Chain\n- Played With\n- Passport FC & Transfer Destination\n\nIntegrating a lightweight daily puzzle section provides an effortless retention loop for users on non-match days while increasing session duration.\n\nPreview the games here: https://playmaker.best\n\nWould someone on your product or partnerships team be open to a quick 10-minute chat to discuss potential integration?\n\nBest regards,\n\nPlaymaker Team\nhttps://playmaker.best"
  },
  {
    company: "365Scores",
    category: "Live Scores & Alerts",
    email: "Partners@365scores.com",
    fallbackChannel: "Advertisers Email",
    fallbackUrl: "Advertisers@365scores.com",
    subject: "Turnkey Daily Football Mini-Games for 365Scores",
    body: "Hi 365Scores Partnerships Team,\n\n365Scores commands one of the most engaged sports notification audiences in the world.\n\nWe developed Playmaker (https://playmaker.best), a turnkey arcade of daily football knowledge games (Top Transfers, Player Chain, Played With, Passport FC).\n\nEmbedding a daily mini-game tab inside 365Scores gives fans a compelling reason to open the app every morning between matchdays.\n\nYou can test today's live puzzles here: https://playmaker.best\n\nCould we schedule a brief introductory call to explore piloting this for your users?\n\nBest regards,\n\nPlaymaker Team\nhttps://playmaker.best"
  },
  {
    company: "Livesport / Flashscore",
    category: "Live Scores & Media",
    email: "info@livesport.eu",
    fallbackChannel: "Sales Portal",
    fallbackUrl: "https://www.livesport.eu/sales",
    subject: "Editorial Integration: Daily Football Trivia Puzzles (Flashscore)",
    body: "Hi Livesport Team,\n\nAs the network powering Flashscore across global markets, you deliver real-time match data to millions of fans.\n\nWe built Playmaker (https://playmaker.best), a clean, high-performance daily football puzzle suite featuring games like Top Transfers, Player Chain, Played With, and Passport FC.\n\nIntegrating a lightweight daily football quiz into Flashscore's news section offers an effortless way to keep sports fans engaged between matchdays with zero maintenance required.\n\nYou can test the puzzles directly at: https://playmaker.best\n\nWould you be open to connecting us with the relevant person on your business development team?\n\nBest regards,\n\nPlaymaker Team\nhttps://playmaker.best"
  }
];

/**
 * Creates custom UI menu in Google Spreadsheet
 */
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu("⚽ Playmaker Outreach")
    .addItem("1. 🇪🇸 Inicializar pestaña 'Outreach - Spanish'", "setupSpanishOutreachTab")
    .addItem("2. 🇬🇧 Inicializar pestaña 'Outreach - English'", "setupEnglishOutreachTab")
    .addSeparator()
    .addItem("3. 🔍 Auto-Prospectar y añadir dominios (En vivo)", "promptProspectDomains")
    .addSeparator()
    .addItem("4. 📨 Enviar correos pendientes (Pestaña Activa)", "batchSendActiveTabOutreach")
    .addItem("5. 🔍 Detectar rebotados (Bounces) desde Gmail", "detectAndMarkBounces")
    .addSeparator()
    .addItem("6. 🔄 Resetear estados a 'READY' (Pestaña Activa)", "resetActiveTabToReady")
    .addToUi();
}

/**
 * Sets up a designated outreach sheet with leads & headers
 */
function setupSheetTab(tabName, leads) {
  const ss = getTargetSpreadsheet();
  let sheet = ss.getSheetByName(tabName);
  
  if (!sheet) {
    sheet = ss.insertSheet(tabName);
  }
  
  const existingRows = sheet.getLastRow();
  if (existingRows <= 1) {
    sheet.clear();
    sheet.appendRow(HEADERS);

    leads.forEach(lead => {
      sheet.appendRow([
        "READY",
        lead.company,
        lead.category,
        lead.email,
        lead.fallbackChannel,
        lead.fallbackUrl,
        lead.subject,
        lead.body,
        "",
        ""
      ]);
    });
  }

  // Format header row
  const headerRange = sheet.getRange(1, 1, 1, HEADERS.length);
  headerRange.setBackground("#0E0E0E")
             .setFontColor("#39FF14")
             .setFontWeight("bold")
             .setHorizontalAlignment("center");

  // Status dropdown validation
  const statusRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(["READY", "SENT", "BOUNCED", "FALLBACK_SENT", "SKIP", "ERROR"], true)
    .build();
  sheet.getRange(2, 1, Math.max(sheet.getLastRow() - 1, 1), 1).setDataValidation(statusRule);

  // Column widths
  sheet.setFrozenRows(1);
  sheet.setColumnWidth(1, 110); // Status
  sheet.setColumnWidth(2, 220); // Company
  sheet.setColumnWidth(3, 160); // Category
  sheet.setColumnWidth(4, 230); // Primary Email
  sheet.setColumnWidth(5, 180); // Fallback Channel
  sheet.setColumnWidth(6, 260); // Fallback URL / Handle
  sheet.setColumnWidth(7, 300); // Subject
  sheet.setColumnWidth(8, 420); // Body
  sheet.setColumnWidth(9, 170); // Timestamp
  sheet.setColumnWidth(10, 250); // Notes / Log

  Logger.log("Tab " + tabName + " configured with " + leads.length + " leads.");
  return "Setup completed for " + tabName;
}

function setupSpanishOutreachTab() {
  return setupSheetTab(OUTREACH_TAB_ES, SPANISH_LEADS);
}

function setupEnglishOutreachTab() {
  return setupSheetTab(OUTREACH_TAB_EN, ENGLISH_LEADS);
}

/**
 * 🔍 Interactive UI Modal to auto-prospect domains directly inside Google Sheets
 */
function promptProspectDomains() {
  const ui = SpreadsheetApp.getUi();
  const response = ui.prompt(
    "🔍 Auto-Prospectar Nuevas Webs / Apps de Fútbol",
    "Introduce uno o varios dominios (separados por coma o salto de línea):\nEjemplo: managingmadrid.com, whoareya.com, fotmob.com",
    ui.ButtonSet.OK_CANCEL
  );

  if (response.getSelectedButton() !== ui.Button.OK) return;
  const text = response.getResponseText().trim();
  if (!text) return;

  const langResponse = ui.prompt(
    "Idioma de la propuesta",
    "¿En qué idioma quieres redactar las propuestas para estos dominios?\nEscribe ES (Español) o EN (Inglés):",
    ui.ButtonSet.OK_CANCEL
  );
  if (langResponse.getSelectedButton() !== ui.Button.OK) return;
  const isSpanish = !langResponse.getResponseText().trim().toUpperCase().includes("EN");

  const rawDomains = text.split(/[\n,;]+/);
  let addedCount = 0;
  let errors = [];

  rawDomains.forEach(raw => {
    const d = raw.trim();
    if (d) {
      try {
        const res = prospectAndAddDomain(d, isSpanish);
        if (res && res.success) addedCount++;
      } catch (err) {
        errors.push(d + " (" + (err.message || String(err)) + ")");
      }
    }
  });

  const tabName = isSpanish ? OUTREACH_TAB_ES : OUTREACH_TAB_EN;
  let summaryMsg = "✅ ¡Proceso completado!\nSe agregaron " + addedCount + " prospectos nuevos a la pestaña '" + tabName + "' listos para enviar.";
  if (errors.length > 0) {
    summaryMsg += "\n\n⚠️ No se pudieron analizar:\n- " + errors.join("\n- ");
  }
  ui.alert("Resultado de Auto-Prospección", summaryMsg, ui.ButtonSet.OK);
}

/**
 * Crawls a domain, extracts emails/forms/socials, creates tailored pitch, and appends to Sheet
 */
function prospectAndAddDomain(rawDomain, isSpanish) {
  let domain = rawDomain.trim().toLowerCase()
    .replace(/^https?:\/\//i, "")
    .replace(/\/.*$/, "")
    .replace(/^www\./i, "");

  if (!domain || !domain.includes(".")) {
    throw new Error("Dominio inválido");
  }

  const ss = getTargetSpreadsheet();
  const tabName = isSpanish ? OUTREACH_TAB_ES : OUTREACH_TAB_EN;
  let sheet = ss.getSheetByName(tabName);
  if (!sheet) {
    if (isSpanish) setupSpanishOutreachTab();
    else setupEnglishOutreachTab();
    sheet = ss.getSheetByName(tabName);
  }

  // Prevent duplicates
  const existingData = sheet.getDataRange().getValues();
  for (let r = 1; r < existingData.length; r++) {
    const existingEmail = String(existingData[r][3] || "").toLowerCase();
    const existingUrl = String(existingData[r][5] || "").toLowerCase();
    const existingNotes = String(existingData[r][9] || "").toLowerCase();
    if (existingUrl.includes(domain) || existingNotes.includes(domain) || (existingEmail && existingEmail.includes(domain))) {
      return { success: false, duplicate: true, domain: domain };
    }
  }

  // 1. Fetch Homepage
  let html = "";
  let homeUrl = "https://" + domain;
  try {
    const res = UrlFetchApp.fetch(homeUrl, {
      muteHttpExceptions: true,
      followRedirects: true,
      headers: { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" }
    });
    if (res.getResponseCode() === 200) {
      html = res.getContentText() || "";
    }
  } catch (e) {
    try {
      homeUrl = "http://" + domain;
      const res = UrlFetchApp.fetch(homeUrl, { muteHttpExceptions: true, followRedirects: true });
      html = res.getContentText() || "";
    } catch (e2) {}
  }

  // Extract Company Name / Title
  let company = domain.split(".")[0];
  company = company.charAt(0).toUpperCase() + company.slice(1);
  const titleMatch = html.match(/<title[^>]*>([^<]+)<\/title>/i);
  if (titleMatch && titleMatch[1]) {
    const rawTitle = titleMatch[1].split(/[-–|:•]/)[0].trim();
    if (rawTitle.length >= 2 && rawTitle.length <= 40) {
      company = rawTitle;
    }
  }

  // Extract Emails
  const emailRegex = /[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+/g;
  let foundEmails = html.match(emailRegex) || [];
  let cleanEmails = [];
  foundEmails.forEach(e => {
    const em = e.toLowerCase().trim();
    if (!em.match(/\.(png|jpg|jpeg|gif|svg|webp|css|js)$/i) &&
        !em.includes("example.com") &&
        !em.includes("wixpress") &&
        !em.includes("sentry") &&
        !cleanEmails.includes(em)) {
      cleanEmails.push(em);
    }
  });

  // 2. Fetch Contact subpage if needed
  let fallbackFormUrl = "";
  const subpages = isSpanish ?
    ["contacto", "contact", "acerca", "about", "publicidad", "aviso-legal"] :
    ["contact", "contact-us", "about", "about-us", "advertise"];

  for (let s = 0; s < subpages.length; s++) {
    const subUrl = "https://" + domain + "/" + subpages[s];
    try {
      const subRes = UrlFetchApp.fetch(subUrl, {
        muteHttpExceptions: true,
        followRedirects: true,
        headers: { "User-Agent": "Mozilla/5.0" }
      });
      if (subRes.getResponseCode() === 200) {
        fallbackFormUrl = subUrl;
        const subHtml = subRes.getContentText() || "";
        const subMatches = subHtml.match(emailRegex) || [];
        subMatches.forEach(e => {
          const em = e.toLowerCase().trim();
          if (!em.match(/\.(png|jpg|jpeg|gif|svg|webp)$/i) && !cleanEmails.includes(em)) {
            cleanEmails.push(em);
          }
        });
        if (cleanEmails.length > 0) break;
      }
    } catch (e) {}
  }

  // 3. Extract Social handles
  let twitterHandle = "";
  let linkedinUrl = "";
  const twMatch = html.match(/(?:twitter\.com|x\.com)\/([a-zA-Z0-9_]{1,30})/i);
  if (twMatch && !twMatch[1].match(/(share|intent|home|search)/i)) {
    twitterHandle = "@" + twMatch[1];
  }
  const liMatch = html.match(/linkedin\.com\/(?:company|in)\/([a-zA-Z0-9_-]+)/i);
  if (liMatch) {
    linkedinUrl = "https://linkedin.com/company/" + liMatch[1];
  }

  // Primary Email selection (prefer contact/info/sales/partnerships or first)
  let primaryEmail = "";
  if (cleanEmails.length > 0) {
    const preferred = cleanEmails.find(e => e.includes("contact") || e.includes("info") || e.includes("partner") || e.includes("sales") || e.includes("redaccion"));
    primaryEmail = preferred || cleanEmails[0];
  }

  // Build Fallback Details
  let fallbackChannel = "Web Form / Direct";
  let fallbackUrl = fallbackFormUrl || ("https://" + domain);
  if (twitterHandle) {
    fallbackUrl += " (Twitter: " + twitterHandle + ")";
    fallbackChannel = fallbackFormUrl ? "Web Form / Twitter DM" : "Twitter DM";
  } else if (linkedinUrl) {
    fallbackUrl += " (LinkedIn: " + linkedinUrl + ")";
    fallbackChannel = fallbackFormUrl ? "Web Form / LinkedIn" : "LinkedIn";
  }

  // Build Subjects & Bodies
  let subject = "";
  let body = "";

  if (isSpanish) {
    subject = "Mini-juegos de fútbol diarios para " + company + ": Retención y tiempo de sesión";
    body = "Hola equipo de " + company + ",\n\n" +
           "Sigo el contenido y la comunidad futbolera que han construido en " + domain + ".\n\n" +
           "Desarrollamos Playmaker (https://playmaker.best/es/), una plataforma de mini-juegos diarios de fútbol tipo Wordle basados en datos reales de fichajes y trayectorias (Top Fichajes, Cadena de Jugadores, Jugó Con, Pasaporte FC).\n\n" +
           "Integrar un reto diario o widget en " + company + " aporta:\n" +
           "1. Retención entre jornadas: un hábito recurrente para entrar a la web o app cada mañana.\n" +
           "2. Mayor tiempo de permanencia en página (dwell time), beneficiando directamente sus ingresos publicitarios.\n" +
           "3. Cero mantenimiento: la rotación diaria de estadísticas se procesa de forma 100% autónoma.\n\n" +
           "Pueden probar los juegos en directo aquí: https://playmaker.best/es/\n\n" +
           "¿Tendrían 5 minutos esta semana para ver si tiene encaje para su audiencia?\n\n" +
           "Un saludo cordial,\n\nPlaymaker Team\nhttps://playmaker.best";
  } else {
    subject = "Daily Interactive Football Mini-Games for " + company + " (User Retention & Dwell Time)";
    body = "Hi " + company + " Team,\n\n" +
           "We follow your platform and football coverage on " + domain + ".\n\n" +
           "We built Playmaker (https://playmaker.best), an arcade of daily football knowledge games powered by verified historical data (Top Transfers, Player Chain, Played With, Passport FC).\n\n" +
           "Embedding a lightweight daily mini-game or widget on " + company + " provides:\n" +
           "1. Mid-week user retention: gives fans a compelling reason to visit every morning between match fixtures.\n" +
           "2. Increased average session duration (dwell time) to lift programmatic ad RPMs.\n" +
           "3. Zero engineering burden: fully automated daily puzzle generation.\n\n" +
           "You can test today's live puzzles here: https://playmaker.best\n\n" +
           "Would someone on your partnerships or digital product team be open to a quick 10-minute chat?\n\n" +
           "Best regards,\n\nPlaymaker Team\nhttps://playmaker.best";
  }

  const initialStatus = primaryEmail ? "READY" : "FALLBACK_SENT";
  const notesLog = primaryEmail ? "Auto-prospectado desde " + domain : "Sin email público detectado. Usar Fallback Channel";

  sheet.appendRow([
    initialStatus,
    company,
    isSpanish ? "Medio Deportivo / Web" : "Sports Media / Web",
    primaryEmail,
    fallbackChannel,
    fallbackUrl,
    subject,
    body,
    "",
    notesLog
  ]);

  // Apply status dropdown validation to newly appended row
  const lastRow = sheet.getLastRow();
  const statusRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(["READY", "SENT", "BOUNCED", "FALLBACK_SENT", "SKIP", "ERROR"], true)
    .build();
  sheet.getRange(lastRow, 1).setDataValidation(statusRule);

  return { success: true, company: company, email: primaryEmail, domain: domain };
}

/**
 * Sends pending emails for the currently selected active tab (or Spanish by default)
 */
function batchSendActiveTabOutreach() {
  const ss = getTargetSpreadsheet();
  let sheet = ss.getActiveSheet();
  
  if (!sheet || (sheet.getName() !== OUTREACH_TAB_ES && sheet.getName() !== OUTREACH_TAB_EN)) {
    sheet = ss.getSheetByName(OUTREACH_TAB_ES);
  }

  if (!sheet) {
    throw new Error("No se encontró la pestaña de outreach. Ejecuta la inicialización primero.");
  }

  const data = sheet.getDataRange().getValues();
  if (data.length <= 1) return { sent: 0, errors: 0 };

  let sentCount = 0;
  let errorCount = 0;

  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    const status = String(row[0] || "").trim().toUpperCase();
    const company = row[1];
    const recipient = String(row[3] || "").trim();
    const subject = row[6];
    const body = row[7];
    const rowIndex = i + 1;

    if (status === "READY" && recipient && recipient.includes("@")) {
      try {
        GmailApp.sendEmail(recipient, subject, body, {
          name: SENDER_NAME
        });

        sheet.getRange(rowIndex, 1).setValue("SENT");
        sheet.getRange(rowIndex, 9).setValue(new Date().toISOString());
        sheet.getRange(rowIndex, 10).setValue("Successfully dispatched via Gmail");
        sentCount++;
        Logger.log("Sent email to: " + recipient + " (" + company + ")");

        Utilities.sleep(1200);
      } catch (err) {
        errorCount++;
        sheet.getRange(rowIndex, 1).setValue("ERROR");
        sheet.getRange(rowIndex, 10).setValue(err.message || String(err));
        Logger.log("Error sending to " + recipient + ": " + err);
      }
    }
  }

  Logger.log("Batch complete on " + sheet.getName() + ". Sent: " + sentCount + ", Errors: " + errorCount);
  return { sent: sentCount, errors: errorCount };
}

/**
 * 🔍 AUTOMATED BOUNCE DETECTION:
 * Scans user's Gmail inbox for Delivery Status Notifications (Failure),
 * identifies the bounced recipient, and automatically updates the Sheet status to 'BOUNCED'!
 */
function detectAndMarkBounces() {
  const ss = getTargetSpreadsheet();
  const tabs = [OUTREACH_TAB_ES, OUTREACH_TAB_EN];
  let totalBouncedFound = 0;

  // Search recent failure notices in Gmail (past 14 days)
  const query = 'from:mailer-daemon "Delivery Status Notification (Failure)" newer_than:14d';
  const threads = GmailApp.search(query, 0, 40);
  
  if (threads.length === 0) {
    Logger.log("No delivery failure emails found in Gmail.");
    return { bounced: 0 };
  }

  tabs.forEach(tabName => {
    const sheet = ss.getSheetByName(tabName);
    if (!sheet) return;

    const data = sheet.getDataRange().getValues();
    if (data.length <= 1) return;

    // Map email -> rowIndex
    const emailToRow = {};
    for (let r = 1; r < data.length; r++) {
      const email = String(data[r][3] || "").trim().toLowerCase();
      if (email) emailToRow[email] = r + 1;
    }

    threads.forEach(thread => {
      const messages = thread.getMessages();
      messages.forEach(msg => {
        const bodyText = (msg.getPlainBody() || "").toLowerCase();
        
        for (const targetEmail in emailToRow) {
          if (bodyText.includes(targetEmail)) {
            const rowIndex = emailToRow[targetEmail];
            const currentStatus = String(data[rowIndex - 1][0] || "").trim().toUpperCase();

            if (currentStatus !== "BOUNCED") {
              sheet.getRange(rowIndex, 1).setValue("BOUNCED");

              // Extract snippet of why it failed
              let failureReason = "Address rejected / mailbox not found by server";
              const rawBody = msg.getPlainBody();
              const match = rawBody.match(/The response from the remote server was:\s*([^\n\r]+)/i) ||
                            rawBody.match(/because the address couldn't be found/i);
              if (match && match[1]) {
                failureReason = match[1].trim().substring(0, 140);
              }

              sheet.getRange(rowIndex, 10).setValue("BOUNCED: " + failureReason + " (Use Fallback Channel)");
              totalBouncedFound++;
              Logger.log("Marked BOUNCED in " + tabName + " for: " + targetEmail);
            }
          }
        }
      });
    });
  });

  Logger.log("Bounce detection complete. Total bounced emails marked: " + totalBouncedFound);
  return { bounced: totalBouncedFound };
}

/**
 * Resets rows in active tab back to READY
 */
function resetActiveTabToReady() {
  const ss = getTargetSpreadsheet();
  let sheet = ss.getActiveSheet();
  if (!sheet) sheet = ss.getSheetByName(OUTREACH_TAB_ES);
  if (!sheet) return;

  const lastRow = sheet.getLastRow();
  if (lastRow > 1) {
    for (let r = 2; r <= lastRow; r++) {
      const current = sheet.getRange(r, 1).getValue();
      if (current !== "SKIP") {
        sheet.getRange(r, 1).setValue("READY");
        sheet.getRange(r, 9).setValue("");
        sheet.getRange(r, 10).setValue("");
      }
    }
  }
}

/**
 * HTTP Web App Endpoints
 */
function doGet(e) {
  const action = (e && e.parameter && e.parameter.action) || "bounces";
  
  if (action === "bounces") {
    const res = detectAndMarkBounces();
    return ContentService.createTextOutput(JSON.stringify({ status: "ok", action: "bounces", result: res }))
      .setMimeType(ContentService.MimeType.JSON);
  }

  if (action === "setup_es") {
    const res = setupSpanishOutreachTab();
    return ContentService.createTextOutput(JSON.stringify({ status: "ok", action: "setup_es", result: res }))
      .setMimeType(ContentService.MimeType.JSON);
  }

  if (action === "setup_en") {
    const res = setupEnglishOutreachTab();
    return ContentService.createTextOutput(JSON.stringify({ status: "ok", action: "setup_en", result: res }))
      .setMimeType(ContentService.MimeType.JSON);
  }

  return ContentService.createTextOutput(JSON.stringify({ status: "unknown_action", action: action }))
    .setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  try {
    let payload = {};
    if (e && e.postData && e.postData.contents) {
      try {
        payload = JSON.parse(e.postData.contents);
      } catch (err) {}
    }
    const action = payload.action || (e && e.parameter && e.parameter.action);

    if (action === "prospect_domain") {
      const domain = payload.domain || e.parameter.domain;
      const isSpanish = payload.isSpanish !== undefined ? payload.isSpanish : (e && e.parameter && e.parameter.isSpanish !== "false");
      const res = prospectAndAddDomain(domain, isSpanish);
      return ContentService.createTextOutput(JSON.stringify({ status: "ok", result: res }))
        .setMimeType(ContentService.MimeType.JSON);
    }
  } catch(err) {
    return ContentService.createTextOutput(JSON.stringify({ status: "error", message: err.message }))
      .setMimeType(ContentService.MimeType.JSON);
  }
  return doGet(e);
}
