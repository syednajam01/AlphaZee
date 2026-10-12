import './styles/main.css';
import { startStorefront } from './utils/startup.js';

startStorefront(() => import('./app.js'));
