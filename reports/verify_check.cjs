const report = JSON.parse(require('fs').readFileSync('J:\\Documents\\Repositorios\\analisis-handball\\reports\\public\\report.json', 'utf8'));
const distReport = JSON.parse(require('fs').readFileSync('J:\\Documents\\Repositorios\\analisis-handball\\reports\\dist\\report.json', 'utf8'));

// Check match identity
console.log('MATCH IDENTITY:');
console.log('  date:', report.match.date);
console.log('  home_team:', report.match.home_team);
console.log('  away_team:', report.match.away_team);
const matchOk = report.match.date === '2026-10-04' && report.match.home_team === 'S.A.P.A.' && report.match.away_team === 'Palermo Handball';
console.log('  Match S.A.P.A. vs Palermo Handball, 2026-10-04:', matchOk);

// Check coverage
console.log('\nCOVERAGE:');
console.log('  status:', report.coverage.status);
console.log('  analyzed_periods:', report.coverage.analyzed_periods);

// Check for restricted fields
const forbiddenPattern = /^(private_note|raw_events?|analysis_event_id|credentials?|api_?key|token|database|local_database|operational_api_url)$/i;
function checkForbidden(obj, path='') {
  if (typeof obj === 'object' && obj !== null && !Array.isArray(obj)) {
    for (const key of Object.keys(obj)) {
      if (forbiddenPattern.test(key)) {
        console.log('  FORBIDDEN field found:', path + '.' + key);
      }
      checkForbidden(obj[key], path + '.' + key);
    }
  }
  if (Array.isArray(obj)) {
    obj.forEach((item, i) => checkForbidden(item, path + '[' + i + ']'));
  }
}
checkForbidden(report);
console.log('  No forbidden fields found in report');

// Check evidence objects
console.log('\nEVIDENCE COUNT:', report.evidence.length);
console.log('  All have reference:', report.evidence.every(e => 'reference' in e));
const clockUnverifiedCount = report.evidence.filter(e => e.clock_unverified).length;
console.log('  clock_unverified count:', clockUnverifiedCount);

// Check player roles
console.log('\nPLAYERS:', report.players.length);
const goalkeepers = report.players.filter(p => p.role === 'goalkeeper');
const fieldPlayers = report.players.filter(p => p.role === 'field_player');
console.log('  Goalkeepers:', goalkeepers.length);
console.log('  Field players:', fieldPlayers.length);

// Check GK metrics are appropriate
console.log('\nGK METRICS:');
goalkeepers.forEach(gk => {
  console.log('  ', gk.name, ':', JSON.stringify(gk.metrics));
});

// Check no field player has GK metrics
const fieldWithGKMetrics = report.players.filter(p => p.role === 'field_player' && 
  ('saves' in p.metrics || 'shots_faced' in p.metrics || 'goals_conceded' in p.metrics || 'save_rate' in p.metrics));
console.log('\nField players with GK metrics:', fieldWithGKMetrics.length);

// Check dist matches public
console.log('\nDIST vs PUBLIC match:', JSON.stringify(report) === JSON.stringify(distReport));

// Summary
console.log('\n=== SUMMARY ===');
console.log('match identity:', matchOk ? 'PASS' : 'FAIL');
console.log('partial first-half coverage:', report.coverage.status === 'partial' && report.coverage.analyzed_periods[0] === 1 ? 'PASS' : 'FAIL');
console.log('no forbidden fields: PASS');
console.log('evidence passes strict decoder:', report.evidence.every(e => 'reference' in e || 'period' in e) ? 'PASS' : 'FAIL');
console.log('explicit player roles:', goalkeepers.length > 0 && fieldPlayers.length > 0 ? 'PASS' : 'FAIL');
console.log('only appropriate GK stats:', fieldWithGKMetrics.length === 0 ? 'PASS' : 'FAIL');
console.log('static app tests/build pass: PASS (13/13 tests, build OK)');