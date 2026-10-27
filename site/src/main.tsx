import "@fontsource/atkinson-hyperlegible-next/400.css";
import "@fontsource/atkinson-hyperlegible-next/700.css";
import "./styles.css";
import { render } from "preact";
import { App } from "./app";
import { initPwa } from "./pwa";

render(<App />, document.getElementById("app")!);
initPwa();
