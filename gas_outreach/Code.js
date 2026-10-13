/**
 * Playmaker - Spanish Outreach Automation
 * Bound to Google Spreadsheet: 1ZNJ57i7kVUYrdW4q4S3lRe4NqYUM7-lL4RQtSzX0_8Q
 */

const OUTREACH_TAB_NAME = "Outreach - Spanish";
const SENDER_NAME = "Playmaker Team";
const SPREADSHEET_ID = "1ZNJ57i7kVUYrdW4q4S3lRe4NqYUM7-lL4RQtSzX0_8Q";

/**
 * Returns active spreadsheet if run from UI, or falls back to opening by ID
 */
function getTargetSpreadsheet() {
  try {
    const active = SpreadsheetApp.getActiveSpreadsheet();
    if (active) return active;
  } catch (e) {}
  return SpreadsheetApp.openById(SPREADSHEET_ID);
}

const SPANISH_LEADS = [
  {
    company: "Biwenger (Diario AS)",
    category: "Fantasy Football",
    email: "contacto@biwenger.com",
    subject: "Mini-juegos de fútbol diarios para Biwenger: Retención entre jornadas y tiempo de sesión",
    body: "Hola equipo de Biwenger,\n\nEn Biwenger tienen la mayor comunidad fantasy de LaLiga en España, pero como toda plataforma fantasy, existe el reto de mantener a los usuarios entrando a la app de lunes a jueves cuando no hay partidos en juego.\n\nDesarrollamos Playmaker (https://playmaker.best/es/), una suite de mini-juegos diarios de fútbol basados en datos estadísticos y de mercado: Top Fichajes, Cadena de Jugadores, Jugó Con, Destino de Fichaje y Pasaporte FC.\n\nNuestros juegos encajan de forma natural con el perfil de usuario de Biwenger, que analiza constantemente trayectorias y fichajes. Podríamos ofrecerles:\n1. Widget o sección in-app \"El Reto del Día\": Embebido sin fricción ni coste de desarrollo para ustedes.\n2. Gamificación entre jornadas: Los usuarios pueden jugar a diario para ganar créditos/trofeos fantasy o competir con los miembros de su propia liga.\n3. Cero mantenimiento: La actualización de datos y retos diarios se procesa de forma autónoma.\n\nPueden probar los retos en vivo aquí: https://playmaker.best/es/\n\n¿Tendrían 5 minutos esta semana para explorar una colaboración o piloto conjunto?\n\nUn saludo cordial,\n\nPlaymaker Team\nhttps://playmaker.best"
  },
  {
    company: "Mister Fantasy (Champion Games)",
    category: "Fantasy Football",
    email: "marc@championgames.com",
    subject: "Gamificación diaria para Mister Fantasy: Mini-juegos de retención entre jornadas",
    body: "Hola Marc,\n\nTe escribo porque sigo el desarrollo de Mister Fantasy y la experiencia tan cuidada que han creado para los managers de fútbol.\n\nDesarrollamos Playmaker (https://playmaker.best/es/), un arcade de mini-juegos diarios de fútbol tipo Wordle pero basados en datos reales de mercado y carreras de futbolistas (Top Fichajes, Cadena de Jugadores, Jugó Con, Destino de Fichaje y Pasaporte FC).\n\nEl usuario de Mister Fantasy es precisamente el perfil que más disfruta recordando traspasos y compañeros de equipo. Pensamos que integrar un módulo o webview de \"Desafío del Día\" dentro de Mister Fantasy aportaría:\n- Un incentivo diario para abrir la app de lunes a viernes (reduciendo el valle de actividad entre jornadas).\n- Mayor tiempo de sesión por usuario activo.\n- Integración llave en mano, sin carga técnica para su equipo de desarrollo.\n\nPueden probar los modos de juego directamente en https://playmaker.best/es/\n\n¿Te interesaría que tengamos una breve llamada de 10 minutos para ver si tiene encaje para la app?\n\nUn saludo,\n\nPlaymaker Team\nhttps://playmaker.best"
  },
  {
    company: "FútbolFantasy",
    category: "Alineaciones & Fantasy",
    email: "admin@futbolfantasy.com",
    subject: "Widget de juegos interactivos de fútbol para FútbolFantasy (dwell time y engagement)",
    body: "Hola equipo de FútbolFantasy,\n\nFútbolFantasy es la web de referencia absoluta para quienes seguimos LaLiga y el fantasy a diario. Sus usuarios pasan mucho tiempo leyendo previas y posibles alineaciones.\n\nDesarrollamos Playmaker (https://playmaker.best/es/), una colección de mini-juegos diarios de fútbol basados en estadísticas y traspasos (Top Fichajes, Cadena de Jugadores, Jugó Con, Pasaporte FC).\n\nIntegrar un widget responsive de Playmaker en los laterales o al final de los artículos de FútbolFantasy permitiría:\n- Aumentar el tiempo medio de permanencia en página (dwell time), beneficiando directamente el rendimiento publicitario (RPM) y el SEO.\n- Dar a sus lectores un juego diario gratuito y rápido relacionado con el club del que están consultando la previa.\n- Cero mantenimiento: el contenido se actualiza automáticamente cada día.\n\nPueden ver el funcionamiento de los juegos aquí: https://playmaker.best/es/\n\n¿Les gustaría probar un widget piloto para ver cómo reacciona su audiencia?\n\nUn saludo cordial,\n\nPlaymaker Team\nhttps://playmaker.best"
  },
  {
    company: "Jornada Perfecta",
    category: "Fantasy & Noticias",
    email: "jornadaperfecta@gmail.com",
    subject: "Colaboración interactiva para Jornada Perfecta: Reto diario de fútbol",
    body: "Hola equipo de Jornada Perfecta,\n\nSeguimos de cerca sus análisis y guías fantasy para managers en España.\n\nDesarrollamos Playmaker (https://playmaker.best/es/), una suite de mini-juegos de fútbol diarios basados en estadísticas reales (Top Fichajes, Cadena de Jugadores, Jugó Con, Destino de Fichaje y Pasaporte FC).\n\nCreemos que un widget con \"El Reto del Día\" en su portal o recomendado en su boletín encajaría perfectamente con sus seguidores, incentivando visitas diarias incluso entre semana.\n\nPueden probar los juegos aquí: https://playmaker.best/es/\n\n¿Tendrían unos minutos para ver si les encaja probarlo juntos?\n\nUn saludo cordial,\n\nPlaymaker Team\nhttps://playmaker.best"
  },
  {
    company: "Comunio España",
    category: "Fantasy Football",
    email: "info@comunio.es",
    subject: "Gamificación y mini-juegos diarios de fútbol para Comunio",
    body: "Hola equipo de Comunio,\n\nComunio es la plataforma histórica por excelencia para ligas de amigos en el fútbol español.\n\nDesarrollamos Playmaker (https://playmaker.best/es/), una plataforma de retos de lógica y memoria futbolera diaria (Top Fichajes, Cadena de Jugadores, Jugó Con, Pasaporte FC).\n\nNos encantaría explorar una integración ligera para que los miembros de las comunidades puedan competir a diario en un reto de fútbol rápido entre jornadas, fomentando la actividad en la plataforma de lunes a viernes.\n\nPueden ver los modos de juego en directo en https://playmaker.best/es/\n\n¿Sería posible coordinar unos minutos para comentarlo?\n\nUn saludo cordial,\n\nPlaymaker Team\nhttps://playmaker.best"
  },
  {
    company: "BeSoccer / Resultados de Fútbol",
    category: "Scores & Datos (España)",
    email: "api@besoccer.com",
    subject: "Propuesta interactiva para BeSoccer: Mini-juegos diarios de fútbol integrables",
    body: "Hola equipo de BeSoccer,\n\nConocemos el ecosistema de BeSoccer y la enorme base de datos con la que alimentan a millones de aficionados tanto en España como en Latinoamérica.\n\nHemos desarrollado Playmaker (https://playmaker.best/es/), una plataforma de retos diarios de conocimiento futbolístico basados en datos históricos (Top Fichajes, Cadena de Jugadores, Pasaporte FC, Jugó Con).\n\nDado el perfil de aficionado que entra a BeSoccer a consultar estadísticas, fichajes y resultados, una colaboración para integrar un módulo de mini-juegos dentro de su web o app aportaría:\n- Mayor recurrencia diaria y aumento del tiempo medio por sesión.\n- Una experiencia interactiva ligera y responsive, adaptable como widget o marca compartida.\n- Posibilidad de patrocinar el reto diario con sus propios anunciantes.\n\nPueden ver los juegos en funcionamiento aquí: https://playmaker.best/es/\n\n¿Con quién de su equipo de producto o alianzas podríamos conversar unos minutos para valorar esta opción?\n\nUn saludo cordial,\n\nPlaymaker Team\nhttps://playmaker.best"
  },
  {
    company: "Promiedos",
    category: "Scores & Tablas (Argentina)",
    email: "contact@promiedos.com.ar",
    subject: "Juego futbolero diario para Promiedos (Reto del Día)",
    body: "Hola gente de Promiedos,\n\nTodos los que amamos el fútbol entramos a Promiedos a mirar las tablas, los historiales y los resultados al minuto.\n\nCreamos Playmaker (https://playmaker.best/es/), una web ligera y sin rodeos de desafíos diarios de fútbol pensada para verdaderos fanáticos:\n- Top Fichajes (adivinar los pases récord por club/nacionalidad).\n- Cadena de Jugadores (adivinar al jugador uniendo los clubes de su carrera).\n- Jugó Con (adivinar al futbolista misterioso por sus compañeros de cancha).\n- Pasaporte FC (desbloquear nacionalidades por club).\n\nSabemos que la comunidad de Promiedos es la más futbolera de todas y discute cada dato en los comentarios. Nos encantaría ofrecerles un widget o enlace integrable estilo \"El Juego del Día de Promiedos\", completamente gratuito, ultra-rápido y sin complicaciones técnicas.\n\nPueden probar los juegos acá: https://playmaker.best/es/\n\nSi les copa la idea, avísennos y charlamos cómo armarlo.\n\nAbrazo grande,\n\nPlaymaker Team\nhttps://playmaker.best"
  },
  {
    company: "Relevo (Vocento)",
    category: "Medio Deportivo (España)",
    email: "comunidades@relevo.com",
    subject: "Propuesta interactiva para Relevo: Mini-juegos diarios de fútbol (retención y comunidad)",
    body: "Hola equipo de Relevo,\n\nNos encanta el tono fresco y la forma visual e interactiva con la que conectan con los aficionados en Relevo.\n\nPor eso queríamos presentarles Playmaker (https://playmaker.best/es/): un arcade de pasatiempos diarios de fútbol estilo Wordle, diseñado con una estética moderna e impulsado por datos reales (Top Fichajes, Cadena de Jugadores, Jugó Con, Pasaporte FC, Destino de Fichaje).\n\nCreemos que encaja con la identidad de Relevo para crear una sección de \"El Pasatiempo de Relevo\":\n- Fomenta la conversación y el debate en redes y comentarios cada mañana.\n- Aumenta el tiempo de permanencia en página de los lectores.\n- Integrable de forma inmediata vía iframe responsive o co-branding, con cero carga técnica para su redacción.\n\nPueden probar los juegos en directo aquí: https://playmaker.best/es/\n\n¿Tendrían unos minutos esta semana para ver si tiene encaje para su sección digital o redes?\n\nUn saludo cordial,\n\nPlaymaker Team\nhttps://playmaker.best"
  },
  {
    company: "Revista Panenka",
    category: "Cultura & Revista (España)",
    email: "redaccion@panenka.org",
    subject: "Colaboración interactiva para Panenka: Pasatiempos diarios de cultura y memoria futbolera",
    body: "Hola equipo de Panenka,\n\nPanenka es el hogar de la memoria y la cultura futbolera en nuestro idioma.\n\nDesarrollamos Playmaker (https://playmaker.best/es/), una plataforma de retos diarios donde el valor no está en adivinar marcadores, sino en recordar la historia del juego: trayectorias de futbolistas de culto, fichajes históricos (Top Fichajes), conexiones entre clubes (Cadena de Jugadores) y compañeros de equipo de época (Jugó Con).\n\nCreemos que un módulo interactivo diario en su web o newsletter encajaría con el paladar del lector de Panenka, ofreciendo un pasatiempo diario que pone a prueba la memoria futbolera sin publicidad invasiva ni fricción.\n\nPueden ver cómo funciona en https://playmaker.best/es/\n\n¿Les gustaría que intercambiemos impresiones sobre cómo colaborar?\n\nUn saludo cordial,\n\nPlaymaker Team\nhttps://playmaker.best"
  },
  {
    company: "ElDesmarque (Mediaset)",
    category: "Medio Deportivo (España)",
    email: "redaccion@eldesmarque.com",
    subject: "Módulo de mini-juegos de fútbol para ElDesmarque: Incremento de tiempo en página",
    body: "Hola equipo de ElDesmarque,\n\nNos ponemos en contacto para presentarles una propuesta orientada a enriquecer la experiencia de sus lectores y maximizar el tiempo medio por visita (dwell time) en ElDesmarque.\n\nDesarrollamos Playmaker (https://playmaker.best/es/), una suite de mini-juegos diarios de fútbol basados en datos oficiales (Top Fichajes, Cadena de Jugadores, Jugó Con, Pasaporte FC, Destino de Fichaje).\n\nPara un medio con el volumen y la cobertura club a club de ElDesmarque, integrar un widget interactivo diario ofrece ventajas inmediatas:\n- Aumenta sensiblemente el tiempo de permanencia en la página del artículo.\n- Genera un hábito de regreso diario en los lectores de cada equipo.\n- Es 100% responsive, ligero y autónomo (no requiere intervención de su redacción ni infraestructura de servidores).\n\nPueden probar los juegos en directo aquí: https://playmaker.best/es/\n\n¿Con qué persona de su equipo digital o de producto podríamos valorar una prueba piloto?\n\nUn saludo cordial,\n\nPlaymaker Team\nhttps://playmaker.best"
  },
  {
    company: "Futbol Sites / Bolavip",
    category: "Red de Medios (LatAm)",
    email: "contact@futbolsites.net",
    subject: "Propuesta de Gamificación para la red de Futbol Sites (Bolavip, RedGol): Mini-juegos diarios",
    body: "Hola equipo de Futbol Sites,\n\nConocemos el alcance de su red de medios deportivos en América Latina y el mercado hispano de Estados Unidos (Bolavip, RedGol, DaleAlbo, etc.).\n\nHemos desarrollado Playmaker (https://playmaker.best/es/), una plataforma de juegos diarios de trivia y lógica futbolera basados en datos (Top Fichajes, Cadena de Jugadores, Jugó Con, Pasaporte FC).\n\nLos formatos de daily mini-games han demostrado ser una de las herramientas más efectivas para generar hábitos de retorno diario y elevar el tiempo de permanencia (dwell time) en portales deportivos de alto tráfico.\n\nPodemos ofrecerles:\n- Módulos web embebibles o secciones co-brandeadas para sus portales regionales.\n- Posibilidad de patrocinar los retos diarios con las marcas y casas de apuestas aliadas de su red.\n- Integración llave en mano sin sobrecargar a sus equipos de ingeniería.\n\nPueden ver la plataforma en vivo aquí: https://playmaker.best/es/\n\n¿Podríamos coordinar una breve llamada de 10 minutos con su equipo de alianzas o producto digital?\n\nUn saludo cordial,\n\nPlaymaker Team\nhttps://playmaker.best"
  },
  {
    company: "Somos Invictos",
    category: "Comunidad & Medios (México/LatAm)",
    email: "contacto@somosinvictos.com",
    subject: "Dinámica diaria interactiva para la comunidad de Somos Invictos",
    body: "Hola equipo de Somos Invictos,\n\nSeguimos a diario el contenido y los debates que generan con la comunidad futbolera más apasionada de redes.\n\nCreamos Playmaker (https://playmaker.best/es/), una suite de retos diarios donde los aficionados ponen a prueba cuánto saben de fútbol internacional:\n- Top Fichajes (adivinar las compras récord por equipo o país).\n- Cadena de Jugadores (adivinar al jugador uniendo los clubes de su carrera).\n- Jugó Con (adivinar al futbolista misterioso por los compañeros con los que compartió cancha).\n- Pasaporte FC y Destino de Fichaje.\n\nCreemos que una sección de \"El Reto del Día\" en su web o impulsada en sus canales generaría una interacción masiva, debates diarios en comentarios y una razón más para que la gente entre a su sitio todos los días.\n\nPueden probar los retos en vivo acá: https://playmaker.best/es/\n\n¿Qué les parece si exploramos una colaboración sencilla para su audiencia?\n\nUn saludo cordial,\n\nPlaymaker Team\nhttps://playmaker.best"
  },
  {
    company: "JuanFutbol",
    category: "Medio Joven (México)",
    email: "hey@juanfutbol.com",
    subject: "Retos futboleros diarios para la comunidad de JuanFutbol",
    body: "Hola compas de JuanFutbol,\n\nUstedes tienen la vibra más entretenida y cercana del fútbol digital en México y Latinoamérica.\n\nDesarrollamos Playmaker (https://playmaker.best/es/), una plataforma de mini-juegos diarios de fútbol al estilo Wordle pero con sabor futbolero puro: Top Fichajes, Cadena de Jugadores, Jugó Con y Pasaporte FC.\n\nCreemos que armar una colaboración para que JuanFutbol tenga su propio \"Desafío del Día\" o embeber los juegos en su portal sería un hitazo para su comunidad: engancha en 2 minutos, genera piques en redes y hace que la gente vuelva cada mañana.\n\nPueden echarle un ojo a los juegos aquí: https://playmaker.best/es/\n\n¿Les late que platiquemos 5 minutos para ver cómo podemos armar algo juntos?\n\nUn saludo,\n\nPlaymaker Team\nhttps://playmaker.best"
  },
  {
    company: "La Media Inglesa",
    category: "Comunidad & YouTube (España)",
    email: "info@lamediainglesa.com",
    subject: "Pasatiempo futbolero diario para la comunidad de La Media Inglesa",
    body: "Hola equipo de La Media Inglesa,\n\nSabemos lo mucho que disfruta su comunidad con los debates de historia, transferencias y anécdotas de jugadores en cada directo y video.\n\nDesarrollamos Playmaker (https://playmaker.best/es/), una plataforma de desafíos diarios de memoria futbolera basada en datos reales:\n- Cadena de Jugadores (unir clubes de una trayectoria).\n- Jugó Con (adivinar al jugador a partir de 5 compañeros con los que compartió vestuario).\n- Top Fichajes (los fichajes más caros por club/nacionalidad).\n- Pasaporte FC (sellos progresivos de nacionalidades).\n\nPensamos que integrar o recomendar un reto diario en su web o comunidad sería un complemento perfecto para que sus seguidores pongan a prueba su conocimiento futbolístico cada día.\n\nPueden probar los juegos en directo aquí: https://playmaker.best/es/\n\n¿Les gustaría que conversemos brevemente sobre posibles formas de colaborar?\n\nUn saludo cordial,\n\nPlaymaker Team\nhttps://playmaker.best"
  }
];

/**
 * Creates custom UI menu in Google Spreadsheet
 */
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu("⚽ Playmaker Outreach")
    .addItem("1. Inicializar / Poblar pestaña 'Outreach - Spanish'", "setupOutreachTab")
    .addSeparator()
    .addItem("2. Enviar correos pendientes (Status: READY)", "batchSendSpanishOutreach")
    .addItem("3. Resetear todos los estados a 'READY'", "resetAllToReady")
    .addToUi();
}

/**
 * Initializes or refreshes the 'Outreach - Spanish' sheet tab
 */
function setupOutreachTab() {
  const ss = getTargetSpreadsheet();
  let sheet = ss.getSheetByName(OUTREACH_TAB_NAME);
  
  if (!sheet) {
    sheet = ss.insertSheet(OUTREACH_TAB_NAME);
  }
  
  const headers = [
    "Status",
    "Company / Entity",
    "Category",
    "Recipient Email",
    "Subject",
    "Email Body",
    "Sent Timestamp",
    "Notes / Log"
  ];

  // Check if already populated
  const existingRows = sheet.getLastRow();
  if (existingRows <= 1) {
    sheet.clear();
    sheet.appendRow(headers);

    SPANISH_LEADS.forEach(lead => {
      sheet.appendRow([
        "READY",
        lead.company,
        lead.category,
        lead.email,
        lead.subject,
        lead.body,
        "",
        ""
      ]);
    });
  }

  // Format header row
  const headerRange = sheet.getRange(1, 1, 1, headers.length);
  headerRange.setBackground("#0E0E0E")
             .setFontColor("#39FF14")
             .setFontWeight("bold")
             .setHorizontalAlignment("center");

  // Status column dropdown validation
  const statusRule = SpreadsheetApp.newDataValidation()
    .requireValueInList(["READY", "SENT", "SKIP", "ERROR"], true)
    .build();
  sheet.getRange(2, 1, Math.max(sheet.getLastRow() - 1, 1), 1).setDataValidation(statusRule);

  // Formatting and alignment
  sheet.setFrozenRows(1);
  sheet.setColumnWidth(1, 100); // Status
  sheet.setColumnWidth(2, 220); // Company
  sheet.setColumnWidth(3, 160); // Category
  sheet.setColumnWidth(4, 230); // Email
  sheet.setColumnWidth(5, 320); // Subject
  sheet.setColumnWidth(6, 450); // Body
  sheet.setColumnWidth(7, 180); // Timestamp
  sheet.setColumnWidth(8, 200); // Notes

  Logger.log("Outreach - Spanish tab setup complete with " + SPANISH_LEADS.length + " leads.");
  return "Setup completed successfully!";
}

/**
 * Sends all emails marked as 'READY' in the 'Outreach - Spanish' tab.
 */
function batchSendSpanishOutreach() {
  const ss = getTargetSpreadsheet();
  const sheet = ss.getSheetByName(OUTREACH_TAB_NAME);
  
  if (!sheet) {
    throw new Error("Pestaña '" + OUTREACH_TAB_NAME + "' no encontrada. Ejecuta 'setupOutreachTab' primero.");
  }

  const data = sheet.getDataRange().getValues();
  if (data.length <= 1) {
    Logger.log("No leads found in sheet.");
    return { sent: 0, errors: 0 };
  }

  let sentCount = 0;
  let errorCount = 0;

  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    const status = String(row[0] || "").trim().toUpperCase();
    const company = row[1];
    const recipient = String(row[3] || "").trim();
    const subject = row[4];
    const body = row[5];
    const rowIndex = i + 1; // 1-indexed

    if (status === "READY" && recipient && recipient.includes("@")) {
      try {
        GmailApp.sendEmail(recipient, subject, body, {
          name: SENDER_NAME
        });

        // Update status to SENT
        sheet.getRange(rowIndex, 1).setValue("SENT");
        sheet.getRange(rowIndex, 7).setValue(new Date().toISOString());
        sheet.getRange(rowIndex, 8).setValue("Successfully sent by " + SENDER_NAME);
        sentCount++;
        Logger.log("Sent email to: " + recipient + " (" + company + ")");

        // Polite delay to prevent rate limit spikes
        Utilities.sleep(1200);
      } catch (err) {
        errorCount++;
        sheet.getRange(rowIndex, 1).setValue("ERROR");
        sheet.getRange(rowIndex, 8).setValue(err.message || String(err));
        Logger.log("Error sending to " + recipient + ": " + err);
      }
    }
  }

  Logger.log("Batch finished. Sent: " + sentCount + ", Errors: " + errorCount);
  return { sent: sentCount, errors: errorCount };
}

/**
 * Resets all non-SKIP rows to READY
 */
function resetAllToReady() {
  const ss = getTargetSpreadsheet();
  const sheet = ss.getSheetByName(OUTREACH_TAB_NAME);
  if (!sheet) return;
  
  const lastRow = sheet.getLastRow();
  if (lastRow > 1) {
    for (let r = 2; r <= lastRow; r++) {
      const current = sheet.getRange(r, 1).getValue();
      if (current !== "SKIP") {
        sheet.getRange(r, 1).setValue("READY");
        sheet.getRange(r, 7).setValue("");
        sheet.getRange(r, 8).setValue("");
      }
    }
  }
}

/**
 * Web App HTTP Endpoints (doGet / doPost)
 */
function doGet(e) {
  const action = (e && e.parameter && e.parameter.action) || "setup";
  
  if (action === "setup") {
    const msg = setupOutreachTab();
    return ContentService.createTextOutput(JSON.stringify({ status: "ok", action: "setup", result: msg }))
      .setMimeType(ContentService.MimeType.JSON);
  }
  
  if (action === "send") {
    const res = batchSendSpanishOutreach();
    return ContentService.createTextOutput(JSON.stringify({ status: "ok", action: "send", result: res }))
      .setMimeType(ContentService.MimeType.JSON);
  }

  return ContentService.createTextOutput(JSON.stringify({ status: "unknown_action", action: action }))
    .setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  return doGet(e);
}
