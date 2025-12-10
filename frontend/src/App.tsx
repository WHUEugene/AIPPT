import { HashRouter, Route, Routes } from 'react-router-dom';
import Welcome from './pages/Welcome';
import TemplateSelect from './pages/TemplateSelect';
import TemplateCreate from './pages/TemplateCreate';
import ContentInput from './pages/ContentInput';
import Workspace from './pages/Workspace';
import History from './pages/History';

export default function App() {
  return (
    <HashRouter>
      <Routes>
        <Route path="/" element={<Welcome />} />
        <Route path="/templates" element={<TemplateSelect />} />
        <Route path="/create-template" element={<TemplateCreate />} />
        <Route path="/input" element={<ContentInput />} />
        <Route path="/workspace" element={<Workspace />} />
        <Route path="/history" element={<History />} />
      </Routes>
    </HashRouter>
  );
}
