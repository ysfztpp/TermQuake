import "@fontsource/atkinson-hyperlegible-next/400.css";
import "@fontsource/atkinson-hyperlegible-next/700.css";
import "./styles.css";
import { render } from "preact";
import { App } from "./app";
import { initPwa } from "./pwa";
import { loadPrefs } from "./storage";
import { applyTheme, asTheme } from "./theme";

// Before the first render, so the page never shows the wrong colours.
applyTheme(asTheme(loadPrefs().theme));

render(<App />, document.getElementById("app")!);
initPwa();
