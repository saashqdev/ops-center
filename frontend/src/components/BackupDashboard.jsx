import React, { useState } from 'react';
import {
  Container, Paper, Tabs, Tab, Box
} from '@mui/material';
import BackupManager from './BackupManager.jsx';
import BackupSettings from './BackupSettings.jsx';
import {
  Backup as BackupIcon,
  Settings as SettingsIcon
} from '@mui/icons-material';

function TabPanel({ children, value, index }) {
  return (
    <div hidden={value !== index}>
      {value === index && <Box>{children}</Box>}
    </div>
  );
}

export default function BackupDashboard() {
  const [tabValue, setTabValue] = useState(0);

  const handleTabChange = (event, newValue) => {
    setTabValue(newValue);
  };

  const handleSettingsSave = (settings) => {
    console.log('Settings saved:', settings);
    // Here you would typically save settings to environment or config file
  };

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      <Paper sx={{ mb: 3 }}>
        <Tabs value={tabValue} onChange={handleTabChange} aria-label="backup tabs">
          <Tab icon={<BackupIcon />} label="Backups" iconPosition="start" />
          <Tab icon={<SettingsIcon />} label="Settings" iconPosition="start" />
        </Tabs>
      </Paper>

      <TabPanel value={tabValue} index={0}>
        <BackupManager />
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        <BackupSettings onSave={handleSettingsSave} />
      </TabPanel>
    </Container>
  );
}
