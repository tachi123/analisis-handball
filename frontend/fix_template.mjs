import fs from 'fs';
let content = fs.readFileSync('src/components/IncidentWizard.tsx', 'utf8');

content = content.replace(
  '{submitting ? \'Registrando…\' : `Registrar ${formData.outcome === \'goal\' ? \'GOL\' : formData.outcome}`}',
  'submitting\n            ? \'Registrando…\'\n            : formData.outcome === \'goal\'\n              ? \'Registrar GOL\'\n              : `Registrar ${formData.outcome}`'
);

fs.writeFileSync('src/components/IncidentWizard.tsx', content);
console.log('Done');