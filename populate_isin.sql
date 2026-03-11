-- Population initiale de la table isin_utilisateurs
-- Généré le 2026-03-11 depuis isin_actions + actions_par_utilisateur

INSERT INTO isin_utilisateurs (utilisateur, ticker, isin, categorie) VALUES

-- Michel PEA
('Michel', 'PANX.PA', 'FR0014003TT8', 'PEA'),
('Michel', 'CW8.PA', 'FR0011607148', 'PEA'),
('Michel', 'PAEEM.PA', 'FR0013412020', 'PEA'),
('Michel', 'PUST.PA', 'FR0013407236', 'PEA'),
('Michel', 'PSP5.PA', 'FR0011871128', 'PEA'),
('Michel', 'ASML', 'NL0000285116', 'PEA'),
('Michel', 'STMPA.PA', 'FR0000124141', 'PEA'),
('Michel', 'IFX.DE', 'DE0006231004', 'PEA'),
('Michel', 'NP5.DE', 'IT0003506015', 'PEA'),

-- Michel TITRES
('Michel', 'SATS', 'US2787681061', 'TITRES'),
('Michel', 'DBX', 'US2574671090', 'TITRES'),
('Michel', 'COIN', 'US1911021031', 'TITRES'),
('Michel', 'PYPL', 'US70450Y1038', 'TITRES'),
('Michel', 'ZM', 'US98156N1067', 'TITRES'),
('Michel', 'MSFT', 'US5949181044', 'TITRES'),
('Michel', 'AAPL', 'US0378331005', 'TITRES'),
('Michel', 'TSLA', 'US90384T1077', 'TITRES'),
('Michel', 'NFLX', 'US6311021038', 'TITRES'),
('Michel', 'AMZN', 'US0231351067', 'TITRES'),
('Michel', '005930.KS', 'KR7005930003', 'TITRES'),
('Michel', 'NEE', 'US65339F1012', 'TITRES'),
('Michel', 'TSM', 'US8740391003', 'TITRES'),
('Michel', 'STX', 'US78463X1075', 'TITRES'),
('Michel', 'MU', 'US5951121038', 'TITRES'),

-- Romain PEA
('Romain', 'FGR.PA', 'FR0000035093', 'PEA'),
('Romain', 'SOI.PA', 'FR0000121663', 'PEA'),
('Romain', 'PSP5.PA', 'FR0011871128', 'PEA'),
('Romain', 'PCEU.PA', 'FR0013412038', 'PEA'),
('Romain', 'STMPA.PA', 'FR0000124141', 'PEA'),
('Romain', 'DSY.PA', 'FR0000124141', 'PEA'),
('Romain', 'WPEA.PA', 'IE0002XZSHO1', 'PEA'),
('Romain', 'C50.PA', 'LU1681047236', 'PEA'),
('Romain', 'PAASI.PA', 'FR0013412012', 'PEA'),
('Romain', 'VIE.PA', 'FR0000124141', 'PEA'),
('Romain', 'CHIP.PA', 'LU1900066033', 'PEA'),
('Romain', 'PAEEM.PA', 'FR0013412020', 'PEA'),
('Romain', 'AM.PA', 'FR0014004L86', 'PEA'),
('Romain', 'BAYN.DE', 'DE000BAY0017', 'PEA'),
('Romain', 'DEEZR.PA', 'FR001400AYG6', 'PEA'),
('Romain', 'LSG.OL', 'NO0003096208', 'PEA'),

-- Romain TITRES
('Romain', 'FORSE.PA', 'FR0014005SB3', 'TITRES'),
('Romain', 'SATS', 'US2787681061', 'TITRES'),

-- Roger PEA
('Roger', 'SAF.PA', 'FR0000120274', 'PEA'),
('Roger', 'AIR', 'FR0000113220', 'PEA'),
('Roger', 'ASML', 'NL0000285116', 'PEA'),
('Roger', 'NEE', 'US65339F1012', 'PEA'),
('Roger', 'DFNS', 'LU1681047236', 'PEA'),
('Roger', 'RYAAY', 'IE00BYSNTY28', 'PEA'),
('Roger', 'BAYN.DE', 'DE000BAY0017', 'PEA'),

-- Roger TITRES
('Roger', 'SATS', 'US2787681061', 'TITRES'),
('Roger', 'TSM', 'US8740391003', 'TITRES'),
('Roger', 'NVDA', 'US67066G1040', 'TITRES'),
('Roger', 'STX', 'US78463X1075', 'TITRES'),
('Roger', 'GOOGL', 'US02079K3059', 'TITRES'),
('Roger', 'AIBD', 'LU1681047236', 'TITRES'),
('Roger', 'CCJ', 'CA1368951081', 'TITRES'),
('Roger', 'AVGO', 'US109378X1051', 'TITRES'),
('Roger', 'VST', 'US91844X1088', 'TITRES'),
('Roger', 'V', 'US92826C8394', 'TITRES'),
('Roger', 'AMD', 'US0079031078', 'TITRES'),
('Roger', 'ATLX', 'US04785V1016', 'TITRES'),
('Roger', 'PDN.AX', 'AU000000PDN6', 'TITRES'),
('Roger', 'RHM.DE', 'DE0007030009', 'TITRES'),
('Roger', 'NET', 'US64106L1061', 'TITRES'),
('Roger', 'REGN', 'US75886B1075', 'TITRES'),
('Roger', 'FRE.DE', 'DE0005785604', 'TITRES'),
('Roger', 'LRN', 'US5366541060', 'TITRES'),
('Roger', 'PLTR', 'US69745J1060', 'TITRES'),
('Roger', 'ABVX', 'FR0014003TT8', 'TITRES'),
('Roger', 'MSFT', 'US5949181044', 'TITRES'),
('Roger', 'AAPL', 'US0378331005', 'TITRES'),
('Roger', 'META', 'US30303M1027', 'TITRES'),
('Roger', 'AGI', 'CA02107B1076', 'TITRES'),
('Roger', 'MU', 'US5951121038', 'TITRES')

ON DUPLICATE KEY UPDATE isin = VALUES(isin), categorie = VALUES(categorie);
